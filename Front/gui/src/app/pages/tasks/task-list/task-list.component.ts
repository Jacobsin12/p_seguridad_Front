import { CommonModule } from '@angular/common';
import { Component, OnInit, Renderer2 } from '@angular/core';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SplitterModule } from 'primeng/splitter';
import { DragDropModule } from 'primeng/dragdrop';
import { ButtonModule } from 'primeng/button';
import { Task } from '../../../core/models/task.model';
import { TasksService } from '../tasks.service';

interface KanbanTask {
  id: number;
  name: string;
  description: string;
  create_at: string;
  deadline: string;
  color: string;
}

interface KanbanColumn {
  header: string;
  tasks: KanbanTask[];
}

@Component({
  selector: 'app-task-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    SplitterModule,
    DragDropModule,
    ButtonModule
  ],
  templateUrl: './task-list.component.html',
  styleUrls: ['./task-list.component.css']
})
export class TaskListComponent implements OnInit {
  formGroup: FormGroup;
  kanbanBoard: KanbanColumn[] = [
    {
      header: 'En Progreso',
      tasks: [
        {
          id: 1,
          name: 'Desarrollar página de inicio',
          description: 'Crear interfaz de autenticación de usuarios',
          create_at: '2025-07-15T10:00:00',
          deadline: '2025-07-20T17:00:00',
          color: 'blue'
        },
        {
          id: 2,
          name: 'Configuración de base de datos',
          description: 'Configurar base de datos PostgreSQL',
          create_at: '2025-07-14T09:00:00',
          deadline: '2025-07-19T15:00:00',
          color: 'blue'
        }
      ]
    },
    {
      header: 'Revisión',
      tasks: [
        {
          id: 3,
          name: 'Revisar endpoints API',
          description: 'Verificar documentación y respuestas de la API',
          create_at: '2025-07-13T11:00:00',
          deadline: '2025-07-18T16:00:00',
          color: 'orange'
        }
      ]
    },
    {
      header: 'Completado',
      tasks: [
        {
          id: 4,
          name: 'Configuración inicial',
          description: 'Inicialización del proyecto completada',
          create_at: '2025-07-10T08:00:00',
          deadline: '2025-07-12T12:00:00',
          color: 'green'
        }
      ]
    },
    {
      header: 'Pausado',
      tasks: [
        {
          id: 5,
          name: 'Diseño de UI',
          description: 'Pausado por retroalimentación del cliente',
          create_at: '2025-07-11T14:00:00',
          deadline: '2025-07-25T17:00:00',
          color: 'gray'
        }
      ]
    }
  ];

  draggedTask: KanbanTask | null = null;
  draggedFromColumn: KanbanColumn | null = null;
  darkMode: boolean = false;

  constructor(
    private fb: FormBuilder,
    private tasksService: TasksService,
    private renderer: Renderer2
  ) {
    this.formGroup = this.fb.group({
      color: ['#1976D2']
    });

    const savedMode = localStorage.getItem('darkMode');
    this.darkMode = savedMode ? JSON.parse(savedMode) : false;
  }

  ngOnInit(): void {
    this.applyDarkMode();
  }

  applyDarkMode(): void {
    if (this.darkMode) {
      this.renderer.addClass(document.body, 'dark-mode');
    } else {
      this.renderer.removeClass(document.body, 'dark-mode');
    }
  }

  toggleDarkMode(): void {
    this.darkMode = !this.darkMode;
    localStorage.setItem('darkMode', JSON.stringify(this.darkMode));
    this.applyDarkMode();
  }

  dragStart(task: KanbanTask, column: KanbanColumn): void {
    this.draggedTask = task;
    this.draggedFromColumn = column;
  }

  drop(column: KanbanColumn): void {
    if (this.draggedTask && this.draggedFromColumn) {
      // Remover la tarea de la columna original
      const sourceTasks = this.draggedFromColumn.tasks;
      const taskIndex = sourceTasks.findIndex(t => t.id === this.draggedTask!.id);
      if (taskIndex !== -1) {
        sourceTasks.splice(taskIndex, 1);
      }

      // Agregar la tarea a la nueva columna
      column.tasks.push({
        ...this.draggedTask,
        color: this.getColorForStatus(column.header)
      });

      // Limpiar referencias
      this.draggedTask = null;
      this.draggedFromColumn = null;
    }
  }

  dragEnd(): void {
    this.draggedTask = null;
    this.draggedFromColumn = null;
  }

  getColorForStatus(status: string): string {
    switch (status) {
      case 'En Progreso': return 'blue';
      case 'Revisión': return 'orange';
      case 'Completado': return 'green';
      case 'Pausado': return 'gray';
      default: return 'gray';
    }
  }

  getTaskColor(color: string) {
    return {
      'task-blue': color === 'blue',
      'task-green': color === 'green',
      'task-gray': color === 'gray',
      'task-red': color === 'red',
      'task-orange': color === 'orange'
    };
  }
}