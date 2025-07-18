import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig } from '@angular/core';
import { provideAnimations } from '@angular/platform-browser/animations';

import Aura from '@primeng/themes/aura';
import { providePrimeNG } from 'primeng/config';

import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { authInterceptor } from '../app/core/auth/auth-interceptor.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideAnimations(),
    provideRouter(routes),
    providePrimeNG({
      theme: {
        preset: Aura
      }
    }),
    provideHttpClient(withInterceptors([authInterceptor]))
  ]
};