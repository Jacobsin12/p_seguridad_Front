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

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Crear la aplicación Flask
app = Flask(__name__)

# Clave secreta para firmar los tokens JWT
SECRET_KEY = 'A9d$3f8#GjLqPwzVx7!KmRtYsB2eH4Uw'

# Nombre del archivo de base de datos SQLite
DB_NAME = os.path.join(BASE_DIR, 'main_database.db')

# Función para inicializar la base de datos y crear la tabla de usuarios si no existe


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

# Ruta para registrar un nuevo usuario (método POST)


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()  # Obtener datos JSON enviados en la solicitud

    # Validar que se reciban los campos requeridos
    if not data or 'username' not in data or 'password' not in data or 'email' not in data:
        # Responder con error si falta algún campo
        return jsonify({'error': 'Faltan campos'}), 400

    # Hashear la contraseña para guardar de forma segura en la base de datos
    hashed_password = generate_password_hash(data['password'])
    totp_secret = pyotp.random_base32()

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            # Insertar nuevo usuario en la tabla users
            cursor.execute("INSERT INTO users (username, password, email, totp_secret) VALUES (?, ?, ?, ?)",
                           (data['username'], hashed_password, data['email'], totp_secret))
            conn.commit()  # Guardar cambios en la base de datos
            user_id = cursor.lastrowid  # Obtener ID del usuario recién creado
            # Genera un URI compatible con apps como Google Authenticator, usando el nombre de usuario y el secreto TOTP
            otp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
                name=data['username'], issuer_name="SeguridadApp")
            # Genera una imagen QR a partir del URI (el usuario la escaneará con su app 2FA)
            qr = qrcode.make(otp_uri)
            # Crea un buffer en memoria para guardar la imagen sin necesidad de escribir un archivo
            buf = io.BytesIO()
            # Guarda la imagen QR en el buffer en formato PNG
            qr.save(buf, format='PNG')
            # Codifica el contenido del buffer (imagen) en base64 para poder enviarla como texto
            qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            # Genera una URL de imagen embebida en base64 para mostrarla directamente en HTML
            qr_url = f"data:image/png;base64,{qr_b64}"

        # Responder con mensaje de éxito y el ID del usuario creado
        return jsonify({'message': 'Usuario registrado correctamente', 'user_id': user_id, 'qrCodeUrl': qr_url}), 201

    except sqlite3.IntegrityError:
        # Si el nombre de usuario ya existe (restricción UNIQUE), devolver error 409 (conflicto)
        return jsonify({'error': 'Nombre de usuario ya existe'}), 409

# Ruta para login de usuarios (método POST)


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()  # Obtener datos JSON de la solicitud

    # Validar que estén los campos requeridos
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Faltan campos'}), 400

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Buscar usuario en la base de datos por username
        cursor.execute("SELECT * FROM users WHERE username = ?",
                       (data['username'],))
        user = cursor.fetchone()

    # user[2] es la contraseña hasheada almacenada
    # Verificar que exista el usuario y que la contraseña ingresada coincida con el hash
    if user and check_password_hash(user[2], data['password']):
        # Crear un token JWT que incluye id, username y expiración a 1 hora
        temp_token = jwt.encode({
            'id': user[0],
            'username': user[1],
            'mfa': True,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        }, SECRET_KEY, algorithm='HS256')

        # Devolver token JWT al cliente
        return jsonify({'tempToken': temp_token}), 200

    # Si usuario no existe o contraseña no coincide, devolver error 401
    return jsonify({'error': 'Credenciales incorrectas'}), 401

# Ruta que maneja la verificación del OTP (One-Time Password)


@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    # Obtiene el encabezado de autorización
    auth_header = request.headers.get('Authorization', '')

    # Verifica si el encabezado Authorization contiene un token tipo Bearer
    if not auth_header.startswith('Bearer'):
        return jsonify({'error': 'Falta token en header'}), 401

    # Extrae el token temporal del encabezado
    temp_token = auth_header.split(' ')[1]

    # Obtiene el cuerpo de la solicitud en formato JSON
    data = request.get_json()

    # Verifica que se haya enviado un código OTP
    if not data or 'otp' not in data:
        return jsonify({'error': 'Falta OTP'}), 400

    try:
        # Decodifica el token temporal (JWT) usando la clave secreta
        payload = jwt.decode(temp_token, SECRET_KEY, algorithms=['HS256'])

        # Verifica si el token incluye la marca de que es parte del proceso MFA
        if not payload.get('mfa'):
            return jsonify({'error': 'Token invalido por MFA'}), 401

        # Obtiene el ID del usuario desde el payload del token
        user_id = payload['id']

        # Conecta con la base de datos SQLite y busca al usuario por su ID
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()

        # Si no se encuentra al usuario, retorna error
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Obtiene el TOTP usando el secreto almacenado en la columna 5 del usuario
        totp = pyotp.TOTP(user[5])

        # Verifica que el OTP proporcionado sea válido
        if totp.verify(data['otp']):
            # Si es válido, genera el token JWT final con 1 hora de validez
            final_token = jwt.encode({
                'id': user[0],
                'username': user[1],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }, SECRET_KEY, algorithm='HS256')

            # Devuelve el token final
            return jsonify({'token': final_token}), 200
        else:
            # Si el OTP es incorrecto
            return jsonify({'error': 'OTP incorrecto'}), 401

    # Si el token ha expirado
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expirado'}), 401

    # Si el token es inválido por cualquier otra razón
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Token invalido'}), 401


# Ejecutar la aplicación Flask
if __name__ == '__main__':
    init_db()  # Crear la base de datos y tabla si no existen
    # Ejecutar en puerto 5001 con debug activado (modo desarrollo)
    app.run(port=5001, debug=True)