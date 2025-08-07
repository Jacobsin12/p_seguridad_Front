import requests
import logging
import time
import json
import jwt
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

# Configuración inicial
app = Flask(__name__)
CORS(app, origins=["http://localhost:4200"])

# Clave secreta igual a la del microservicio de autenticación
SECRET_KEY = 'A9d$3f8#GjLqPwzVx7!KmRtYsB2eH4Uw'

# Configuración del logger en modo JSON
logger = logging.getLogger('gateway_logger')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('gateway_logs.log')
file_handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(file_handler)

# Diccionario de servicios
SERVICES = {
    'auth': 'http://localhost:5001',
    'user': 'http://localhost:5002',
    'tasks': 'http://localhost:5003',
}

# Función para extraer el usuario desde el JWT del header Authorization
def extraer_usuario_desde_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return payload.get("username", "anonimo")
        except jwt.ExpiredSignatureError:
            return "token expirado"
        except jwt.InvalidTokenError:
            return "token inválido"
    return "anonimo"

# Función para registrar en el archivo de logs
def log_request(servicio, method, path, usuario, ip, status_code, response_time):
    log_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "method": method,
        "path": path,
        "servicio": servicio,
        "usuario": usuario,
        "ip": ip,
        "status_code": status_code,
        "response_time_seconds": round(response_time, 3)
    }
    logger.info(json.dumps(log_data))

# Función principal de proxy
def proxy_request(servicio, service_url, path):
    method = request.method
    url = f'{service_url}/{path}'
    usuario = extraer_usuario_desde_token()
    ip = request.remote_addr

    start_time = time.time()
    try:
        resp = requests.request(
            method=method,
            url=url,
            json=request.get_json(silent=True),
            headers={key: value for key, value in request.headers if key.lower() != 'host'}
        )
        duration = time.time() - start_time

        log_request(servicio, method, f'/{path}', usuario, ip, resp.status_code, duration)

        try:
            return jsonify(resp.json()), resp.status_code
        except ValueError:
            return resp.text, resp.status_code

    except Exception as e:
        duration = time.time() - start_time
        log_request(servicio, method, f'/{path}', usuario, ip, 500, duration)
        return jsonify({'error': 'Gateway error'}), 500

# Rutas para redirigir a los microservicios
@app.route('/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy_auth(path):
    return proxy_request('auth', SERVICES['auth'], path)

@app.route('/user/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy_user(path):
    return proxy_request('user', SERVICES['user'], path)

@app.route('/tasks', methods=['GET', 'POST'])
@app.route('/tasks/<path:path>', methods=['GET', 'PUT', 'DELETE'])
def proxy_tasks(path=''):
    fixed_path = 'tasks' if path == '' else f'tasks/{path}'
    return proxy_request('tasks', SERVICES['tasks'], fixed_path)

# Iniciar aplicación
if __name__ == '__main__':
    app.run(port=5000, debug=True)
