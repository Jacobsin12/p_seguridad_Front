import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  let token: string | null = null;

  // Usa tempToken solo para la ruta /verify-otp
  if (req.url.includes('/verify-otp')) {
    token = localStorage.getItem('tempToken');
  } else {
    // Para todo lo demás usa el token final
    token = localStorage.getItem('token');
  }

  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(req);
};
