from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import jwt
import os
import datetime
from functools import wraps
import logging
import traceback
import sys

app = Flask(__name__)

# Configuración de logging para errores detallados
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('task-service.log', mode='a'),
        logging.StreamHandler(sys.stdout)  # Para que se imprima en consola también
    ]
)

# Configuración de CORS
CORS(app, resources={r"/*": {"origins": "http://localhost:4200"}})

# Obtener la URL de la base de datos de la variable de entorno
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    logging.error("La variable de entorno DATABASE_URL no está definida")
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida")

# Configuración de SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("postgres://", "postgresql://")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Clave secreta para JWT
SECRET_KEY = os.getenv('SECRET_KEY', 'A9d$3f8#GjLqPwzVx7!KmRtYsB2eH4Uw')

# Modelo de la tabla tasks
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    create_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    deadline = db.Column(db.DateTime)
    status = db.Column(db.String, nullable=False, default='InProgress')
    is_alive = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(db.Integer, nullable=False)

# Decorador para validar el token JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token requerido'}), 401
        try:
            token = token.replace('Bearer ', '')
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        return f(*args, **kwargs)
    return decorated

# Manejo global de errores para capturar excepciones no controladas
@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Error interno: {str(e)}\n{traceback.format_exc()}")
    return jsonify({"error": "Error interno del servidor"}), 500

# Resto de rutas aquí con sus respectivos try-except y logging...

# Ejemplo para GET /tasks con logging
@app.route('/tasks', methods=['GET'])
@token_required
def get_tasks():
    try:
        logging.info("Entrando en endpoint GET /tasks")
        created_by = request.user['id']
        tasks = Task.query.filter_by(created_by=created_by, is_alive=True).all()
        tasks_list = []
        for t in tasks:
            tasks_list.append({
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'create_at': t.create_at.isoformat(),
                'deadline': t.deadline.isoformat() if t.deadline else None,
                'status': t.status,
                'isAlive': t.is_alive
            })
        return jsonify({'tasks': tasks_list})
    except Exception as e:
        logging.error(f"Error al obtener tareas: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Error al obtener las tareas'}), 500

# Pon similar logging y manejo de errores para las demás rutas...

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=False)
