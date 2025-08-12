import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, Observable, tap } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private apiUrl = 'https://auth-service-ywqa.onrender.com';

  constructor(private http: HttpClient) {}

  // Login: guarda tempToken en localStorage
  login(username: string, password: string): Observable<any> {
    const loginData = { username, password };
    console.debug('AuthService - Enviando login:', loginData);

    return this.http.post<{ tempToken: string }>(`${this.apiUrl}/login`, loginData).pipe(
      tap(response => {
        console.debug('AuthService - Respuesta login:', response);
        if (response?.tempToken) {
          localStorage.setItem('tempToken', response.tempToken);
        }
      }),
      catchError(error => {
        console.debug('AuthService - Error login:', error);
        throw error;
      })
    );
  }

  // Registro (sin cambios)
  register(data: {
    username: string;
    password: string;
    email: string;
    birthdate: string;
    secret_question: string;
    secret_answer: string;
  }): Observable<any> {
    return this.http.post(`${this.apiUrl}/register`, data);
  }

  // Verificación OTP: usa tempToken y guarda token final
  verifyOtp(otp: string): Observable<any> {
    const tempToken = localStorage.getItem('tempToken');

    console.debug('AuthService - Verificando OTP:', { otp, tempToken });

    if (!tempToken || tempToken.trim() === '') {
      console.debug('AuthService - Token temporal vacío');
      throw new Error('Token temporal requerido');
    }

    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${tempToken}`
    });

    const otpData = { otp: otp.trim() };
    console.debug('AuthService - Body enviado:', otpData);

    return this.http.post<{ token: string }>(`${this.apiUrl}/verify-otp`, otpData, { headers }).pipe(
      tap(response => {
        console.debug('AuthService - Respuesta OTP:', response);
        if (response?.token) {
          localStorage.setItem('token', response.token);
          localStorage.removeItem('tempToken');  // Limpia el tempToken porque ya no se usa
        }
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

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('tempToken');
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  }

  debugToken(token: string): void {
    if (!token) {
      console.debug('Token Debug: Token es null o undefined');
      return;
    }
    console.debug('Token Debug:', {
      length: token.length,
      starts: token.substring(0, 20),
      ends: token.substring(token.length - 20),
      isString: typeof token === 'string',
      hasSpaces: token.includes(' ')
    });
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
