import { Routes } from '@angular/router';
import { NotFoundComponent } from './not-found/not-found.component';

export const ERROR_ROUTES: Routes = [
  {
    path: '',
    component: NotFoundComponent
  }
];