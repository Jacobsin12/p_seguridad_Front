import { Routes } from '@angular/router';
import { LogListComponent } from './dash-list/log-list.component';

export const DASH_LOGS_ROUTES: Routes = [
  {
    path: '',
    component: LogListComponent,
  }
];
