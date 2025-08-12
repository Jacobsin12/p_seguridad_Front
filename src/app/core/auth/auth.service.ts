// Importa el servicio HttpClient para realizar peticiones HTTP al backend
import { HttpClient, HttpHeaders } from '@angular/common/http';

// Permite que Angular inyecte esta clase en cualquier componente o servicio
import { Injectable } from '@angular/core';

// Importa operadores de RxJS para trabajar con peticiones asíncronas
import { catchError, Observable, tap } from 'rxjs';

// Este decorador marca el servicio como disponible para toda la app (Singleton)
@Injectable({
  providedIn: 'root',
})
export class AuthService {
  // URL base del backend Flask donde se expone el servicio de autenticación
  private apiUrl = 'https://auth-service-ywqa.onrender.com';

  // Constructor que inyecta el cliente HTTP de Angular
  constructor(private http: HttpClient) {}

  // Método para iniciar sesión
  login(username: string, password: string): Observable<any> {
    // Construye el cuerpo de la solicitud con las credenciales
    const loginData = { username, password };
    console.debug('AuthService - Enviando login:', loginData);
    
    // Hace una petición POST al backend con las credenciales
    return this.http.post(`${this.apiUrl}/login`, loginData).pipe(
      // `tap` permite ver la respuesta sin modificarla
      tap(response => {
        console.debug('AuthService - Respuesta login:', response);
      }),
      // Captura errores en caso de fallo de login
      catchError(error => {
        console.debug('AuthService - Error login:', error);
        throw error;
      })
    );
  }

  // Método para registrar un nuevo usuario
  register(data: {
    username: string;
    password: string;
    email: string;
    birthdate: string;
    secret_question: string;
    secret_answer: string;
  }): Observable<any> {
    // Envía los datos del formulario al endpoint /register
    return this.http.post(`${this.apiUrl}/register`, data);
  }

  // Método para verificar el OTP como parte del 2FA
  verifyOtp(otp: string, tempToken: string): Observable<any> {
    // Muestra parte del token temporal por seguridad en consola
    console.debug('AuthService - Verificando OTP:', {
      otp,
      tempToken: tempToken ? `${tempToken.substring(0, 20)}...` : 'NO TOKEN',
      tokenLength: tempToken ? tempToken.length : 0 
    });

    // Verifica si el token está vacío o nulo
    if (!tempToken || tempToken.trim() === ''){
      console.debug('AuthService - Token temporal vacío');
      throw new Error('Token temporal requerido');
    }

    // Define los headers para la solicitud, incluyendo el token Bearer
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${tempToken}` 
    });

    // Muestra los headers enviados (solo para debug)
    console.debug('AuthService - Headers enviados:', {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${tempToken.substring(0, 20)}...`
    });

    // Construye el cuerpo con el código OTP ingresado
    const otpData = { otp: otp.trim() };
    console.debug('AuthService - Body enviado:', otpData);

    // Hace la solicitud POST para verificar el OTP
    return this.http.post(`${this.apiUrl}/verify-otp`, otpData, { headers }).pipe(
      tap(response => {
        console.debug('AuthService - Respuesta OTP:', response);
      }),
      catchError(error => {
        console.error('AuthService - Error OTP:', {
          status: error.status,
          statusText: error.statusText,
          error: error.error,
          url: error.url,
          headers: error.headers
        });
        throw error;
      })
    );
  }

  // Elimina el token del almacenamiento local (cierra sesión)
  logout(): void {
    localStorage.removeItem('token');
  }

  // Verifica si hay un token guardado → el usuario está autenticado
  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  }

  // Método para depurar un token JWT
  debugToken(token: string): void {
    if (!token) {
      console.debug('Token Debug: Token es null o undefined');
      return;
    }

    // Muestra información del token (inicio, final, longitud, etc.)
    console.debug('Token Debug:', {
      length: token.length,
      starts: token.substring(0, 20),
      ends: token.substring(token.length - 20),
      isString: typeof token === 'string',
      hasSpaces: token.includes(' ')
    });

    // Intenta decodificar el payload del JWT para ver su contenido
    try {
      const parts = token.split('.');
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]));
        console.debug('Token Payload:', payload);
      }
    } catch (e) {
      console.debug('No se pudo decodificar el token:', e);
    }
  }
}