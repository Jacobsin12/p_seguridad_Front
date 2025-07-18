import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface Task {
  id?: number;
  name: string;
  description: string;
  deadline: string;
  status?: string;
  isAlive?: boolean;
  create_at?: string;
}

@Injectable({
  providedIn: 'root'
})
export class TasksService {
  private baseUrl = 'http://localhost:5000/tasks'; // ✅ CORREGIDO

  constructor(private http: HttpClient) {}

  // Obtener todas las tareas
  getTasks(): Observable<any> {
    return this.http.get(this.baseUrl); // ✅ /tasks
  }

  // Obtener una tarea por ID
  getTask(id: number): Observable<any> {
    return this.http.get(`${this.baseUrl}/${id}`);
  }

  // Crear una nueva tarea
  createTask(task: Task): Observable<any> {
    return this.http.post(this.baseUrl, task); // ✅ /tasks
  }

  // Actualizar una tarea existente
  updateTask(id: number, task: Task): Observable<any> {
    return this.http.put(`${this.baseUrl}/${id}`, task); // ✅ /tasks/:id
  }

  // Eliminar una tarea (borrado lógico)
  deleteTask(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/${id}`);
  }
}