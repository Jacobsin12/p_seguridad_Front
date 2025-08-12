import { HttpClient, HttpHeaders } from '@angular/common/http';
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
  private baseUrl = 'https://gateway-sktd.onrender.com/tasks';  // Cambia según tu backend

  constructor(private http: HttpClient) {}

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('token') || '';
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }

  // Obtener todas las tareas
  getTasks(): Observable<any> {
    const headers = this.getAuthHeaders();
    return this.http.get(this.baseUrl, { headers });
  }

  // Obtener una tarea por ID
  getTask(id: number): Observable<any> {
    const headers = this.getAuthHeaders();
    return this.http.get(`${this.baseUrl}/${id}`, { headers });
  }

  // Crear una nueva tarea
  createTask(task: Task): Observable<any> {
    const headers = this.getAuthHeaders();
    return this.http.post(this.baseUrl, task, { headers });
  }

  // Actualizar una tarea existente
  updateTask(id: number, task: Task): Observable<any> {
    const headers = this.getAuthHeaders();
    return this.http.put(`${this.baseUrl}/${id}`, task, { headers });
  }

  // Actualizar solo el estado (status) de una tarea
  updateTaskStatus(id: number, status: string): Observable<any> {
    const headers = this.getAuthHeaders();
    return this.http.put(`${this.baseUrl}/${id}`, { status }, { headers });
  }

  // Eliminar una tarea (borrado lógico)
  deleteTask(id: number): Observable<any> {
    const headers = this.getAuthHeaders();
    return this.http.delete(`${this.baseUrl}/${id}`, { headers });
  }
}
