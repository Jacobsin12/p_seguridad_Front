import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  console.log('Interceptor - URL antes:', req.url);

  const token = localStorage.getItem('token');

  // Si hay token, lo añadimos SIEMPRE a menos que esté en las rutas excluidas
  const excludedRoutes = ['/login', '/register']; // aquí pones solo las que no requieran token
  const shouldExclude = excludedRoutes.some(url => req.url.includes(url));

  if (token && !shouldExclude) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  console.log('Interceptor - URL después:', req.url);
  return next(req);
};
