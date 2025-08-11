import os
import time
import logging
from datetime import datetime
import requests
import jwt
from flask import Flask, jsonify, request, g, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import firebase_admin
from firebase_admin import credentials, firestore
import tempfile
import json
import traceback  # Agregado para capturar trazas de errores

# --- Configuraciones desde variables de entorno ---
SECRET_KEY = os.environ.get('SECRET_KEY', 'A9d$3f8#GjLqPwzVx7!KmRtYsB2eH4Uw')
PORT = int(os.environ.get('PORT', 5000))

AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'https://auth-service-ywqa.onrender.com')
USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'https://user-service-ta15.onrender.com')
TASK_SERVICE_URL = os.environ.get('TASK_SERVICE_URL', 'https://task-service-qomb.onrender.com')

# Firebase credentials JSON desde variable de entorno
firebase_cred_json = os.environ.get('FIREBASE_CREDENTIALS')

if not firebase_admin._apps:
    if firebase_cred_json:
        try:
            with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
                temp.write(firebase_cred_json)
                temp.flush()
                cred = credentials.Certificate(temp.name)
                firebase_admin.initialize_app(cred)
            logging.info("Firebase inicializado correctamente.")
        except Exception as e:
            logging.error(f"Error inicializando Firebase: {str(e)} - Traza: {traceback.format_exc()}")
            raise Exception(f"No se pudo inicializar Firebase: {str(e)}")
    else:
        logging.error("No se encontró la variable de entorno FIREBASE_CREDENTIALS para Firebase")
        raise Exception("No se encontró la variable de entorno FIREBASE_CREDENTIALS para Firebase")

db = firestore.client()

# --- Flask App ---
app = Flask(__name__)

# Ajusta la URL del frontend que usarás en producción
CORS(
    app,
    origins=["http://localhost:4200", "https://appseg.vercel.app"],
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
)

logging.basicConfig(
    filename='apigateway.log',
    level=logging.DEBUG,  # Cambiado a DEBUG para más detalles
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filemode='a'  # Aseguramos modo append para no sobreescribir logs
)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["500 per hour"]
)

def get_user_from_token(token):
    try:
        token = token.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = payload.get("username") or payload.get("user_id") or "unknown"
        logging.debug(f"Usuario extraído del token: {user}")
        return user
    except Exception as e:
        logging.error(f"Error decodificando token: {str(e)} - Traza: {traceback.format_exc()}")
        return "invalid_token"

@app.before_request
def start_timer():
    g.start_time = time.time()
    logging.debug(f"Iniciando solicitud: {request.method} {request.full_path}")

@app.after_request
def log_request(response):
    if not hasattr(g, 'start_time'):
        g.start_time = time.time()

    duration = round(time.time() - g.start_time, 4)
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    status = response.status_code
    method = request.method
    full_path = request.full_path

    raw_token = request.headers.get('Authorization')
    user = get_user_from_token(raw_token) if raw_token else 'anonymous'

    log_message = (
        f"{timestamp} | {method} {full_path} | Status: {status} | Time: {duration}s | User: {user}"
    )
    logging.info(log_message)

    try:
        db.collection('apigateway_logs').add({
            'timestamp': timestamp,
            'method': method,
            'path': full_path,
            'status': status,
            'duration': duration,
            'user': user
        })
        logging.debug("Log guardado en Firestore correctamente.")
    except Exception as e:
        logging.error(f"Error guardando log en Firestore: {str(e)} - Traza: {traceback.format_exc()}")

    return response

def proxy_request(service_url, path):
    method = request.method
    url = f'{service_url}/{path}'

    headers = {key: value for key, value in request.headers if key.lower() != 'host'}

    data = None
    json_data = None
    if method in ['POST', 'PUT', 'PATCH']:
        content_type = request.headers.get('Content-Type', '').lower()
        logging.debug(f"Content-Type recibido: {content_type}")
        if 'application/json' in content_type or content_type == '':
            try:
                # Si Content-Type está vacío, intentamos parsear como JSON si hay body
                if content_type == '' and request.data:
                    logging.warning("Content-Type vacío; asumiendo application/json para body presente.")
                    json_data = json.loads(request.data)
                else:
                    json_data = request.get_json()
                logging.debug(f"Datos JSON enviados: {json_data}")
            except Exception as e:
                logging.error(f"Error parseando JSON: {str(e)} - Traza: {traceback.format_exc()}")
                return jsonify({"error": "Datos JSON inválidos", "details": str(e)}), 400
        elif 'multipart/form-data' in content_type or 'application/x-www-form-urlencoded' in content_type:
            data = request.form.to_dict()
            logging.debug(f"Datos form enviados: {data}")
        else:
            logging.error(f"Content-Type no soportado: {content_type}")
            return jsonify({"error": "Content-Type no soportado", "details": f"Se esperaba 'application/json', recibido '{content_type}'"}), 415

    try:
        logging.debug(f"Enviando solicitud a {url} con método {method}")
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=request.args,
            data=data,
            json=json_data,
            timeout=10
        )
        logging.debug(f"Respuesta recibida de {url}: Status {resp.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error en proxy_request a {url}: {str(e)} - Traza: {traceback.format_exc()}")
        return jsonify({"error": "Error comunicando con el microservicio", "details": str(e)}), 502

    excluded_headers = [
        'content-length', 'transfer-encoding', 'connection',
        'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te',
        'trailers', 'upgrade'
    ]

    response_headers = [(name, value) for (name, value) in resp.headers.items()
                        if name.lower() not in excluded_headers]

    return Response(resp.content, resp.status_code, response_headers)

@app.route('/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@limiter.limit("100/minute")
def proxy_auth(path):
    logging.debug(f"Proxy a auth: {path}")
    return proxy_request(AUTH_SERVICE_URL, path)

@app.route('/user/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy_user(path):
    logging.debug(f"Proxy a user: {path}")
    return proxy_request(USER_SERVICE_URL, path)

@app.route('/tasks', methods=['GET', 'POST'])
@app.route('/tasks/', methods=['GET', 'POST'])
@app.route('/tasks/<path:path>', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def proxy_tasks(path=''):
    fixed_path = 'tasks' if path == '' else f'tasks/{path}'
    logging.debug(f"Proxy a tasks: {fixed_path}")
    return proxy_request(TASK_SERVICE_URL, fixed_path)

@app.route('/api/logs/stats', methods=['GET'])
def logs_stats():
    logging.debug("Accediendo a /api/logs/stats desde Firestore")
    try:
        status_counts = {}
        total_time = 0
        count = 0
        api_counts = {}

        # Consulta los logs más recientes (puedes agregar filtros o paginación si quieres)
        logs_ref = db.collection('apigateway_logs').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1000)
        logs = logs_ref.stream()

        for log in logs:
            data = log.to_dict()
            status_code = str(data.get('status', 'unknown'))
            duration = float(data.get('duration', 0))
            path = data.get('path', 'unknown')

            # Normaliza path para agrupar endpoints (ejemplo: '/tasks/123' a '/tasks')
            if path.startswith('/tasks'):
                path = '/tasks'
            elif path.startswith('/auth'):
                path = '/auth'
            elif path.startswith('/user'):
                path = '/user'

            # Cuenta por status
            status_counts[status_code] = status_counts.get(status_code, 0) + 1

            total_time += duration
            count += 1

            if path not in api_counts:
                api_counts[path] = {'hits': 0, 'total_time': 0}
            api_counts[path]['hits'] += 1
            api_counts[path]['total_time'] += duration

        average_response_time = total_time / count if count > 0 else 0

        endpoints = {}
        for path, data in api_counts.items():
            avg_time = data['total_time'] / data['hits'] if data['hits'] > 0 else 0
            endpoints[path] = {
                'hits': data['hits'],
                'avg_time': round(avg_time, 3)
            }

        return jsonify({
            "total_requests": count,
            "status_counts": status_counts,
            "avg_response_time": round(average_response_time, 3),
            "endpoints": endpoints
        })

    except Exception as e:
        logging.error(f"Error general en logs_stats: {str(e)} - Traza: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    logging.info(f"Iniciando servidor en puerto {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)  # Agregado debug=True para más info en consola