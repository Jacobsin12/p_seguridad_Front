import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SplitterModule } from 'primeng/splitter';
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
    SplitterModule
  ],
  templateUrl: './task-list.component.html',
  styleUrls: ['./task-list.component.css']
})
export class TaskListComponent implements OnInit {
  formGroup: FormGroup;
  kanbanBoard: KanbanColumn[] = [];

  constructor(
    private fb: FormBuilder,
    private tasksService: TasksService
  ) {
    this.formGroup = this.fb.group({
      color: ['#1976D2']
    });
  }

  ngOnInit(): void {
    this.loadTasks();
  }

  loadTasks(): void {
    this.tasksService.getTasks().subscribe({
      next: (res: any) => {
        const tasks: Task[] = res.tasks.map((t: Task) => ({
          ...t,
          create_at: t.create_at,
          deadline: t.deadline
        }));
        this.kanbanBoard = this.groupTasksByStatus(tasks);
      },
      error: (err) => {
        console.error('Error al cargar tareas:', err);
      }
    });
  }

  groupTasksByStatus(tasks: Task[]): KanbanColumn[] {
    const columns: { [key: string]: KanbanTask[] } = {
      InProgress: [],
      Revision: [],
      Completed: [],
      Paused: []
    };

    tasks.forEach((task) => {
      if (columns[task.status]) {
        columns[task.status].push({
          id: task.id,
          name: task.name,
          description: task.description,
          create_at: task.create_at,
          deadline: task.deadline,
          color: this.getColorForStatus(task.status)
        });
      }
    });

    return [
      { header: 'In Progress', tasks: columns['InProgress'] },
      { header: 'Revision', tasks: columns['Revision'] },
      { header: 'Completed', tasks: columns['Completed'] },
      { header: 'Paused', tasks: columns['Paused'] }
    ];
  }

  getColorForStatus(status: string): string {
    switch (status) {
      case 'InProgress': return 'blue';
      case 'Revision': return 'orange';
      case 'Completed': return 'green';
      case 'Paused': return 'gray';
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