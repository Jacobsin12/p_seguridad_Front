# auth_service.py
from flask import Flask, request, jsonify
import pyotp
import qrcode
import io
import base64
import sqlite3
import os
import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Configuración
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(__name__)
SECRET_KEY = 'A9d$3f8#GjLqPwzVx7!KmRtYsB2eH4Uw'
DB_NAME = os.path.join(BASE_DIR, 'main_database.db')

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                status TEXT DEFAULT 'active',
                totp_secret TEXT
            )
        ''')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data or 'email' not in data:
        return jsonify({'error': 'Faltan campos'}), 400

    hashed_password = generate_password_hash(data['password'])
    totp_secret = pyotp.random_base32()

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, email, totp_secret) VALUES (?, ?, ?, ?)",
                           (data['username'], hashed_password, data['email'], totp_secret))
            conn.commit()
            user_id = cursor.lastrowid

        otp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=data['username'], issuer_name="SeguridadApp")
        qr = qrcode.make(otp_uri)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        qr_url = f"data:image/png;base64,{qr_b64}"

        return jsonify({
            'message': 'Usuario registrado correctamente',
            'user_id': user_id,
            'qrCodeUrl': qr_url
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({'error': 'Nombre de usuario ya existe'}), 409

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Faltan campos'}), 400

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (data['username'],))
        user = cursor.fetchone()

    if user and check_password_hash(user[2], data['password']):
        temp_token = jwt.encode({
            'id': user[0],
            'username': user[1],
            'mfa': True,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        }, SECRET_KEY, algorithm='HS256')

        return jsonify({'tempToken': temp_token}), 200

    return jsonify({'error': 'Credenciales incorrectas'}), 401

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Falta token en header Authorization'}), 401
    temp_token = auth_header.split(' ')[1]

    data = request.get_json()
    if not data or 'otp' not in data:
        return jsonify({'error': 'Falta OTP en body'}), 400

    try:
        payload = jwt.decode(temp_token, SECRET_KEY, algorithms=['HS256'])

        if not payload.get('mfa'):
            return jsonify({'error': 'Token inválido para MFA'}), 401

        user_id = payload['id']

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        totp = pyotp.TOTP(user[5])
        if totp.verify(data['otp']):
            final_token = jwt.encode({
                'id': user[0],
                'username': user[1],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }, SECRET_KEY, algorithm='HS256')

            return jsonify({'token': final_token}), 200
        else:
            return jsonify({'error': 'OTP incorrecto'}), 401

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expirado'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Token inválido'}), 401


if __name__ == '__main__':
    init_db()
    app.run(port=5001, debug=True)
