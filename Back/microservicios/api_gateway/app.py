import time
import logging
from datetime import datetime
import requests
import jwt
from flask import Flask, jsonify, request, g, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore

# Inicializa Firebase Admin (ajusta la ruta a tu archivo JSON)
cred = credentials.Certificate('firebase_key.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Clave secreta para decodificar JWT (debe coincidir con el backend auth)
SECRET_KEY = 'A9d$3f8#GjLqPwzVx7!KmRtYsB2eH4Uw'

app = Flask(__name__)
CORS(app, origins=["http://localhost:4200"])

logging.basicConfig(
    filename='apigateway.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["500 per hour"]
)

AUTH_SERVICE_URL = 'http://localhost:5001'
USER_SERVICE_URL = 'http://localhost:5002'
TASK_SERVICE_URL = 'http://localhost:5003'

def get_user_from_token(token):
    try:
        token = token.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("username") or payload.get("user_id") or "unknown"
    except Exception:
        return "invalid_token"

@app.before_request
def start_timer():
    g.start_time = time.time()

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
    except Exception as e:
        print(f"Error guardando log en Firestore: {e}")

    return response

def proxy_request(service_url, path):
    method = request.method
    url = f'{service_url}/{path}'

    headers = {key: value for key, value in request.headers if key.lower() != 'host'}

    data = None
    json_data = None
    if method in ['POST', 'PUT', 'PATCH']:
        if request.is_json:
            json_data = request.get_json()
        else:
            data = request.form.to_dict()

    try:
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=request.args,
            data=data,
            json=json_data,
            timeout=10
        )
    except requests.exceptions.RequestException as e:
        # En caso de error comunicando con microservicio, devolver error controlado
        return jsonify({"error": "Error comunicando con el microservicio", "details": str(e)}), 502

    excluded_headers = [
        'content-encoding', 'content-length', 'transfer-encoding', 'connection',
        'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te',
        'trailers', 'upgrade'
    ]
    response_headers = [(name, value) for (name, value) in resp.headers.items()
                        if name.lower() not in excluded_headers]

    response = Response(resp.content, resp.status_code, response_headers)
    return response

@app.route('/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@limiter.limit("10/minute")
def proxy_auth(path):
    return proxy_request(AUTH_SERVICE_URL, path)

@app.route('/user/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy_user(path):
    return proxy_request(USER_SERVICE_URL, path)

@app.route('/tasks', methods=['GET', 'POST'])
@app.route('/tasks/', methods=['GET', 'POST'])
@app.route('/tasks/<path:path>', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def proxy_tasks(path=''):
    fixed_path = 'tasks' if path == '' else f'tasks/{path}'
    return proxy_request(TASK_SERVICE_URL, fixed_path)

@app.route('/api/logs/stats', methods=['GET'])
def logs_stats():
    try:
        status_counts = {}
        total_time = 0
        count = 0
        api_counts = {}

        with open('apigateway.log', 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) < 5:
                    continue

                status_code = None
                time_sec = None
                path = None

                for part in parts:
                    part = part.strip()
                    if part.startswith('Status:'):
                        status_code = part.split(' ')[1]
                    elif part.startswith('Time:'):
                        try:
                            time_sec = float(part.split(' ')[1].replace('s', ''))
                        except Exception:
                            time_sec = 0
                    elif any(part.startswith(m) for m in ['POST', 'GET', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']):
                        path = part.split(' ')[1]

                if status_code is None or time_sec is None or path is None:
                    continue

                # Normalizar rutas para agrupar /tasks
                if path.startswith('/tasks'):
                    path = '/tasks'

                status_counts[status_code] = status_counts.get(status_code, 0) + 1
                total_time += time_sec
                count += 1

                if path not in api_counts:
                    api_counts[path] = {'hits': 0, 'total_time': 0}
                api_counts[path]['hits'] += 1
                api_counts[path]['total_time'] += time_sec

        average_response_time = total_time / count if count > 0 else 0

        endpoints = {}
        for path, data in api_counts.items():
            avg_time = data['total_time'] / data['hits']
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
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)
