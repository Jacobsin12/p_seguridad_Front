import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  console.log('Interceptor - URL antes:', req.url);

  const token = localStorage.getItem('token');

  if (token && !req.url.includes('/auth/verify-otp')) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  console.log('Interceptor - URL después:', req.url);
  return next(req);
};
