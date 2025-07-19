import { Routes } from '@angular/router';
import { AuthGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/auth/login', pathMatch: 'full' },

  {
    path: 'auth',
    loadChildren: () =>
      import('./pages/auth/auth.routes').then((m) => m.AUTH_ROUTES),
  },

  {
    path: 'task',
    loadChildren: () =>
      import('./pages/tasks/task.routes').then((m) => m.TASK_ROUTES),
  },

  // 🔴 Esta debe ir al final
  {
    path: '**',
    loadChildren: () =>
      import('./pages/errors/error.routes').then((m) => m.ERROR_ROUTES),
  },
];
