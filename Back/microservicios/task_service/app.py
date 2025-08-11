from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import jwt
import os
import datetime
from functools import wraps
import logging
import traceback

app = Flask(__name__)

# Configuración de logging para errores detallados
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='task-service.log',
                    filemode='a')

# Configuración de CORS (ajusta el origen según tu frontend)
CORS(app, resources={r"/*": {"origins": "http://localhost:4200"}})

# Obtener la URL de la base de datos de la variable de entorno
DATABASE_URL = os.getenv('DATABASE_URL')
print(f"DATABASE_URL leída: {DATABASE_URL}")

if not DATABASE_URL:
    logging.error("La variable de entorno DATABASE_URL no está definida")
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("postgres://", "postgresql://")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

SECRET_KEY = os.getenv('SECRET_KEY', 'A9d$3f8#GjLqPwzVx7!KmRtYsB2eH4Uw')

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    deadline = db.Column(db.DateTime)
    status = db.Column(db.Text, nullable=False, default='InProgress')
    isAlive = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(db.Integer, nullable=False)


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
            logging.debug(f"Usuario autenticado: {data}")
            if 'id' not in data:
                return jsonify({'error': 'Token inválido: falta campo id'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        return f(*args, **kwargs)
    return decorated

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Error interno: {str(e)}\n{traceback.format_exc()}")
    return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/test-db')
def test_db():
    try:
        db.session.execute('SELECT 1')
        return jsonify({'db_status': 'ok'})
    except Exception as e:
        logging.error(f"Error en conexión a BD: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'db_status': 'error', 'message': str(e)}), 500

@app.route('/tasks', methods=['POST'])
@token_required
def create_task():
    try:
        data = request.get_json()
        required_fields = ['name', 'description', 'deadline']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'Faltan campos obligatorios'}), 400

        deadline = None
        if data.get('deadline'):
            try:
                deadline = datetime.datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Formato de deadline inválido, debe ser ISO 8601'}), 400

        task = Task(
            name=data['name'],
            description=data['description'],
            deadline=deadline,
            status='InProgress',
            is_alive=True,
            created_by=request.user['id']
        )
        db.session.add(task)
        db.session.commit()
        return jsonify({'message': 'Tarea creada', 'task_id': task.id}), 201

    except Exception as e:
        logging.error(f"Error al crear tarea: {str(e)}\n{traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': 'Error al crear la tarea'}), 500

@app.route('/tasks', methods=['GET'])
@token_required
def get_tasks():
    try:
        created_by = request.user['id']
        tasks = Task.query.filter_by(created_by=created_by, is_alive=True).all()
        tasks_list = []
        for t in tasks:
            tasks_list.append({
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'create_at': t.create_at.isoformat() if t.create_at else None,
                'deadline': t.deadline.isoformat() if t.deadline else None,
                'status': t.status,
                'isAlive': t.is_alive
            })
        return jsonify({'tasks': tasks_list})
    except Exception as e:
        logging.error(f"Error al obtener tareas: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Error al obtener las tareas'}), 500

@app.route('/tasks/<int:task_id>', methods=['GET'])
@token_required
def get_task(task_id):
    try:
        created_by = request.user['id']
        t = Task.query.filter_by(id=task_id, created_by=created_by, is_alive=True).first()
        if not t:
            return jsonify({'error': 'Tarea no encontrada o no autorizada'}), 404
        task = {
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'create_at': t.create_at.isoformat() if t.create_at else None,
            'deadline': t.deadline.isoformat() if t.deadline else None,
            'status': t.status,
            'isAlive': t.is_alive
        }
        return jsonify({'task': task})
    except Exception as e:
        logging.error(f"Error al obtener tarea {task_id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Error al obtener la tarea'}), 500

@app.route('/tasks/<int:task_id>', methods=['PUT'])
@token_required
def update_task(task_id):
    try:
        data = request.get_json()
        created_by = request.user['id']
        task = Task.query.filter_by(id=task_id, created_by=created_by).first()
        if not task:
            return jsonify({'error': 'Tarea no encontrada o no autorizada'}), 404

        allowed_fields = ['name', 'description', 'deadline', 'status', 'isAlive']
        update_fields = {field: data[field] for field in allowed_fields if field in data}

        if not update_fields:
            return jsonify({'error': 'No se proporcionaron campos para actualizar'}), 400

        if 'status' in update_fields and update_fields['status'] not in ['InProgress', 'Revision', 'Completed', 'Paused']:
            return jsonify({'error': 'Estado inválido'}), 400

        for field in update_fields:
            if field == 'deadline':
                try:
                    setattr(task, field, datetime.datetime.fromisoformat(update_fields[field].replace('Z', '+00:00')) if update_fields[field] else None)
                except ValueError:
                    return jsonify({'error': 'Formato de deadline inválido, debe ser ISO 8601'}), 400
            else:
                setattr(task, field, update_fields[field])

        db.session.commit()
        return jsonify({'message': 'Tarea actualizada'})
    except Exception as e:
        logging.error(f"Error al actualizar tarea {task_id}: {str(e)}\n{traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': 'Error al actualizar la tarea'}), 500

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(task_id):
    try:
        created_by = request.user['id']
        task = Task.query.filter_by(id=task_id, created_by=created_by).first()
        if not task:
            return jsonify({'error': 'Tarea no encontrada o no autorizada'}), 404
        task.is_alive = False
        db.session.commit()
        return jsonify({'message': 'Tarea eliminada (borrado lógico)'})
    except Exception as e:
        logging.error(f"Error al eliminar tarea {task_id}: {str(e)}\n{traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': 'Error al eliminar la tarea'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=True)
