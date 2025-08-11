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
    path: 'tasks',
    loadChildren: () =>
      import('./pages/tasks/task.routes').then((m) => m.TASK_ROUTES),
  },

  // Agregas esta ruta para dash-logs
  {
    path: 'dash-logs',
    loadChildren: () =>
      import('./pages/dash-logs/dash-logs.routes').then(m => m.DASH_LOGS_ROUTES),
  },

  // 🔴 Esta debe ir al final
  {
    path: '**',
    loadChildren: () =>
      import('./pages/errors/error.routes').then((m) => m.ERROR_ROUTES),
  },
];
