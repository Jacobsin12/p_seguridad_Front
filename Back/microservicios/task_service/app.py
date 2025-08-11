from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras
import jwt
import os
import datetime
from functools import wraps
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:4200"}})

SECRET_KEY = 'A9d$3f8#GjLqPwzVx7!KmRtYsB2eH4Uw'

# Obtener la URL de la base de datos PostgreSQL desde la variable de entorno de Render
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

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

# Crear tabla tasks si no existe
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            create_at TIMESTAMP NOT NULL,
            deadline TIMESTAMP,
            status VARCHAR(20) CHECK(status IN ('InProgress', 'Revision', 'Completed', 'Paused')) NOT NULL DEFAULT 'InProgress',
            isAlive BOOLEAN NOT NULL DEFAULT TRUE,
            created_by INTEGER NOT NULL -- Asume que usuarios están en otra tabla
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/tasks', methods=['POST'])
@token_required
def create_task():
    data = request.get_json()
    required_fields = ['name', 'description', 'deadline']

    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    created_by = request.user['id']
    create_at = datetime.datetime.utcnow()
    deadline = datetime.datetime.fromisoformat(data['deadline'])
    status = 'InProgress'
    isAlive = True

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (name, description, create_at, deadline, status, isAlive, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (data['name'], data['description'], create_at, deadline, status, isAlive, created_by))
    task_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Tarea creada', 'task_id': task_id}), 201

@app.route('/tasks', methods=['GET'])
@token_required
def get_tasks():
    created_by = request.user['id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT id, name, description, create_at, deadline, status, isAlive FROM tasks WHERE created_by = %s AND isAlive = TRUE', (created_by,))
    tasks = cursor.fetchall()
    cursor.close()
    conn.close()

    tasks_list = []
    for t in tasks:
        tasks_list.append({
            'id': t['id'],
            'name': t['name'],
            'description': t['description'],
            'create_at': t['create_at'].isoformat(),
            'deadline': t['deadline'].isoformat() if t['deadline'] else None,
            'status': t['status'],
            'isAlive': t['isalive']
        })
    return jsonify({'tasks': tasks_list})

@app.route('/tasks/<int:task_id>', methods=['GET'])
@token_required
def get_task(task_id):
    created_by = request.user['id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT id, name, description, create_at, deadline, status, isAlive FROM tasks WHERE id = %s AND created_by = %s AND isAlive = TRUE', (task_id, created_by))
    t = cursor.fetchone()
    cursor.close()
    conn.close()

    if not t:
        return jsonify({'error': 'Tarea no encontrada'}), 404

    task = {
        'id': t['id'],
        'name': t['name'],
        'description': t['description'],
        'create_at': t['create_at'].isoformat(),
        'deadline': t['deadline'].isoformat() if t['deadline'] else None,
        'status': t['status'],
        'isAlive': t['isalive']
    }
    return jsonify({'task': task})

@app.route('/tasks/<int:task_id>', methods=['PUT'])
@token_required
def update_task(task_id):
    data = request.get_json()
    created_by = request.user['id']

    allowed_fields = ['name', 'description', 'deadline', 'status', 'isAlive']
    update_fields = {field: data[field] for field in allowed_fields if field in data}

    if 'status' in update_fields and update_fields['status'] not in ['InProgress', 'Revision', 'Completed', 'Paused']:
        return jsonify({'error': 'Estado inválido'}), 400

    set_clauses = []
    values = []
    for key, val in update_fields.items():
        set_clauses.append(f"{key} = %s")
        if key == 'deadline' and val is not None:
            values.append(datetime.datetime.fromisoformat(val))
        else:
            values.append(val)
    set_clause = ', '.join(set_clauses)

    values.append(task_id)
    values.append(created_by)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        UPDATE tasks SET {set_clause}
        WHERE id = %s AND created_by = %s
    ''', tuple(values))
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()

    if affected == 0:
        return jsonify({'error': 'Tarea no encontrada o no autorizada'}), 404

    return jsonify({'message': 'Tarea actualizada'})

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(task_id):
    created_by = request.user['id']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tasks SET isAlive = FALSE
        WHERE id = %s AND created_by = %s
    ''', (task_id, created_by))
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()

    if affected == 0:
        return jsonify({'error': 'Tarea no encontrada o no autorizada'}), 404

    return jsonify({'message': 'Tarea eliminada (borrado lógico)'})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port)
