import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, Observable, tap } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:5000/auth'; // Tu API Gateway

  constructor(private http: HttpClient) {}

  login(username: string, password: string): Observable<any> {
    const loginData = { username, password };
    console.log('🔐 AuthService - Enviando login:', loginData);
    
    return this.http.post(`${this.apiUrl}/login`, loginData).pipe(
      tap(response => {
        console.log('✅ AuthService - Respuesta login:', response);
      }),
      catchError(error => {
        console.error('❌ AuthService - Error login:', error);
        throw error;
      })
    );
  }

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

  
  verifyOtp(otp: string, tempToken: string): Observable<any> {
    console.log('🔑 AuthService - Verificando OTP:', {
      otp,
      tempToken: tempToken ? `${tempToken.substring(0, 20)}...` : 'NO TOKEN',
      tokenLength: tempToken ? tempToken.length : 0
    });

    // Validar que el token temporal existe
    if (!tempToken || tempToken.trim() === '') {
      console.error('❌ AuthService - Token temporal vacío');
      throw new Error('Token temporal requerido');
    }

    // Preparar headers
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${tempToken}`
    });

    console.log('📤 AuthService - Headers enviados:', {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${tempToken.substring(0, 20)}...`
    });

    const otpData = { otp: otp.trim() };
    console.log('📤 AuthService - Body enviado:', otpData);

    return this.http.post(`${this.apiUrl}/verify-otp`, otpData, { headers }).pipe(
      tap(response => {
        console.log('✅ AuthService - Respuesta OTP:', response);
      }),
      catchError(error => {
        console.error('❌ AuthService - Error OTP:', {
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
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  }

  // Método para debug del token
  debugToken(token: string): void {
    if (!token) {
      console.log('🔍 Token Debug: Token es null o undefined');
      return;
    }

    console.log('🔍 Token Debug:', {
      length: token.length,
      starts: token.substring(0, 20),
      ends: token.substring(token.length - 20),
      isString: typeof token === 'string',
      hasSpaces: token.includes(' ')
    });

    // Intentar decodificar el JWT (solo para debug)
    try {
      const parts = token.split('.');
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]));
        console.log('🔍 Token Payload:', payload);
      }
    } catch (e) {
      console.log('🔍 No se pudo decodificar el token:', e);
    }
  }
}