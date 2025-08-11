from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import pyotp
import qrcode
import io
import base64
import os
import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configuración base de datos desde variable de entorno
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'A9d$3f8#GjLqPwzVx7!KmRtYsB2eH4Uw'

db = SQLAlchemy(app)

# Modelo de usuario
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    status = db.Column(db.String(20), default='active')
    totp_secret = db.Column(db.String(16))

# Crear tablas al inicio de la aplicación
with app.app_context():
    db.create_all()

# Registro de usuario
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data or 'email' not in data:
        return jsonify({'error': 'Faltan campos'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Nombre de usuario ya existe'}), 409

    hashed_password = generate_password_hash(data['password'])
    totp_secret = pyotp.random_base32()

    user = User(username=data['username'], password=hashed_password,
                email=data['email'], totp_secret=totp_secret)
    db.session.add(user)
    db.session.commit()

    otp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=data['username'], issuer_name="SeguridadApp")
    qr = qrcode.make(otp_uri)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    qr_url = f"data:image/png;base64,{qr_b64}"

    return jsonify({'message': 'Usuario registrado correctamente', 'user_id': user.id, 'qrCodeUrl': qr_url}), 201

# Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Faltan campos'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        temp_token = jwt.encode({
            'id': user.id,
            'username': user.username,
            'mfa': True,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({'tempToken': temp_token}), 200
    
    return jsonify({'error': 'Credenciales incorrectas'}), 401

# Verificar OTP
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer'):
        return jsonify({'error': 'Falta token en header'}), 401

    temp_token = auth_header.split(' ')[1]
    data = request.get_json()
    if not data or 'otp' not in data:
        return jsonify({'error': 'Falta OTP'}), 400

    try:
        payload = jwt.decode(temp_token, app.config['SECRET_KEY'], algorithms=['HS256'])
        if not payload.get('mfa'):
            return jsonify({'error': 'Token invalido por MFA'}), 401

        user = User.query.get(payload['id'])
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        totp = pyotp.TOTP(user.totp_secret)
        if totp.verify(data['otp']):
            final_token = jwt.encode({
                'id': user.id,
                'username': user.username,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }, app.config['SECRET_KEY'], algorithm='HS256')

            return jsonify({'token': final_token}), 200
        else:
            return jsonify({'error': 'OTP incorrecto'}), 401
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expirado'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Token invalido'}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)), debug=True)
