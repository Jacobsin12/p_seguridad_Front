import { Routes } from '@angular/router';
import { TaskListComponent } from './task-list/task-list.component';
import { TaskCreateComponent } from './task-create/task-create/task-create.component';

export const TASK_ROUTES: Routes = [
  {
    path: '',
    component: TaskListComponent,
  },
  {
    path: 'create',
    component: TaskCreateComponent,
  },
];
