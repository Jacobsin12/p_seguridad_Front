import { CommonModule } from '@angular/common';
import { Component, OnInit, Renderer2 } from '@angular/core';
import { FormBuilder, FormGroup, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SplitterModule } from 'primeng/splitter';
import { DragDropModule } from 'primeng/dragdrop';
import { ButtonModule } from 'primeng/button';
import { CalendarModule } from 'primeng/calendar';
import { InputTextModule } from 'primeng/inputtext';
import { DialogModule } from 'primeng/dialog';  // Import para modal
import { Task } from '../../../core/models/task.model';
import { TasksService } from '../tasks.service';
import { Router } from '@angular/router';  // <-- Import Router

interface KanbanTask {
  id: number;
  name: string;
  description: string;
  create_at: string;
  deadline: string;
  color?: string;
  status: string;
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
    ButtonModule,
    CalendarModule,
    InputTextModule,
    DialogModule,  // Aquí se agrega el dialog module
  ],
  templateUrl: './task-list.component.html',
  styleUrls: ['./task-list.component.css']
})
export class TaskListComponent implements OnInit {
  taskForm: FormGroup;       // Formulario para crear tarea
  showCreateForm = false;    // Control para mostrar/ocultar formulario modal

  kanbanBoard: KanbanColumn[] = [];
  draggedTask: KanbanTask | null = null;
  draggedFromColumn: KanbanColumn | null = null;
  darkMode: boolean = false;

  constructor(
    private fb: FormBuilder,
    private tasksService: TasksService,
    private renderer: Renderer2,
    private router: Router  // <-- Inyectado Router aquí
  ) {
    this.taskForm = this.fb.group({
      name: ['', Validators.required],
      description: ['', Validators.required],
      deadline: ['', Validators.required]
    });

    const savedMode = localStorage.getItem('darkMode');
    this.darkMode = savedMode ? JSON.parse(savedMode) : false;
  }

  ngOnInit(): void {
    this.applyDarkMode();
    this.loadTasksFromBackend();
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

  toggleCreateForm(): void {
    this.showCreateForm = !this.showCreateForm;
    if (!this.showCreateForm) {
      this.taskForm.reset();
    }
  }

  loadTasksFromBackend(): void {
    this.tasksService.getTasks().subscribe({
      next: (res) => {
        const tasks: KanbanTask[] = res.tasks || [];

        const columns: KanbanColumn[] = [
          { header: 'En Progreso', tasks: [] },
          { header: 'Revisión', tasks: [] },
          { header: 'Completado', tasks: [] },
          { header: 'Pausado', tasks: [] }
        ];

        tasks.forEach(task => {
          let statusUI = '';
          switch (task.status) {
            case 'InProgress': statusUI = 'En Progreso'; break;
            case 'Revision': statusUI = 'Revisión'; break;
            case 'Completed': statusUI = 'Completado'; break;
            case 'Paused': statusUI = 'Pausado'; break;
            default: statusUI = 'Pausado'; break;
          }

          const color = this.getColorForStatus(statusUI);
          const col = columns.find(c => c.header === statusUI);
          if (col) {
            col.tasks.push({ ...task, color });
          }
        });

        this.kanbanBoard = columns;
      },
      error: (err) => {
        console.error('Error cargando tareas:', err);
      }
    });
  }

  dragStart(task: KanbanTask, column: KanbanColumn): void {
    this.draggedTask = task;
    this.draggedFromColumn = column;
  }

  drop(column: KanbanColumn): void {
    if (this.draggedTask && this.draggedFromColumn) {
      const sourceTasks = this.draggedFromColumn.tasks;
      const taskIndex = sourceTasks.findIndex(t => t.id === this.draggedTask!.id);
      if (taskIndex !== -1) {
        sourceTasks.splice(taskIndex, 1);
      }

      // Actualizar estado de la tarea y color
      const updatedTask = {
        ...this.draggedTask,
        status: this.mapHeaderToStatus(column.header),
        color: this.getColorForStatus(column.header)
      };

      column.tasks.push(updatedTask);

      // Actualizar en backend
      this.tasksService.updateTask(updatedTask.id, updatedTask).subscribe({
        next: () => {
          // Opcional: refrescar lista o mostrar mensaje
        },
        error: (err) => {
          console.error('Error actualizando tarea:', err);
          // Opcional: revertir cambios visuales si falla update
          this.loadTasksFromBackend();
        }
      });

      this.draggedTask = null;
      this.draggedFromColumn = null;
    }
  }

  dragEnd(): void {
    this.draggedTask = null;
    this.draggedFromColumn = null;
  }

  mapHeaderToStatus(header: string): string {
    switch (header) {
      case 'En Progreso': return 'InProgress';
      case 'Revisión': return 'Revision';
      case 'Completado': return 'Completed';
      case 'Pausado': return 'Paused';
      default: return 'Paused';
    }
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

  getTaskColor(color?: string) {
    return {
      'task-blue': color === 'blue',
      'task-green': color === 'green',
      'task-gray': color === 'gray',
      'task-red': color === 'red',
      'task-orange': color === 'orange'
    };
  }

  onSubmit(): void {
    if (this.taskForm.invalid) {
      this.taskForm.markAllAsTouched();
      return;
    }

    const newTask: Task = {
      id: 0, // provisional, backend asignará
      name: this.taskForm.value.name,
      description: this.taskForm.value.description,
      deadline: this.taskForm.value.deadline.toISOString(),
      create_at: new Date().toISOString(),
      status: 'InProgress',
      isAlive: true
    };

    this.tasksService.createTask(newTask).subscribe({
      next: () => {
        this.loadTasksFromBackend();
        this.toggleCreateForm();
      },
      error: (err) => {
        console.error('Error creando tarea:', err);
      }
    });
  }

  // NUEVO MÉTODO para navegar al dashboard
  goToDashboard(): void {
    this.router.navigate(['/dash-logs']);
  }
}
