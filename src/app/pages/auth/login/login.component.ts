import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';

import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputGroupModule } from 'primeng/inputgroup';
import { InputGroupAddonModule } from 'primeng/inputgroupaddon';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    CardModule,
    InputTextModule,
    ButtonModule,
    InputGroupModule,
    InputGroupAddonModule,
    MessageModule
  ],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  public text1: string = '';
  public text2: string = '';
  public darkMode: boolean = false;

  // OTP MFA
  public otp: string = '';
  public tempToken: string = '';
  public step: 'credentials' | 'otp' = 'credentials';
  public errorMessage: string = '';
  public isLoading: boolean = false;

  constructor(
    private authService: AuthService,
    private router: Router
  ) {
    // Cargar modo oscuro desde localStorage
    const savedMode = localStorage.getItem('darkMode');
    this.darkMode = savedMode === 'true';
  }

  toggleDarkMode(): void {
    this.darkMode = !this.darkMode;
    // Guardar modo oscuro en localStorage para persistencia
    localStorage.setItem('darkMode', String(this.darkMode));
  }

  onLogin(): void {
    this.errorMessage = '';
    this.isLoading = true;

    if (this.step === 'credentials') {
      this.handleCredentialLogin();
    } else {
      this.handleOtpVerification();
    }
  }

  private handleCredentialLogin(): void {
    if (!this.text1?.trim() || !this.text2?.trim()) {
      this.errorMessage = 'Usuario y contraseña son requeridos';
      this.isLoading = false;
      return;
    }

    console.log('🔐 Enviando credenciales...', {
      username: this.text1,
      password: this.text2
    });

    this.authService.login(this.text1, this.text2).subscribe({
      next: (res) => {
        console.log('✅ Respuesta del login:', res);
        this.isLoading = false;

        if (res.tempToken) {
          console.log('🕒 Token temporal recibido, solicitando OTP');
          this.tempToken = res.tempToken;
          this.step = 'otp';
          this.errorMessage = '';
        } else if (res.token) {
          console.log('🔓 Login exitoso con token completo');
          localStorage.setItem('token', res.token);
          this.router.navigate(['/tasks']);
        } else {
          console.error('❌ Respuesta inesperada del servidor');
          this.errorMessage = 'Respuesta inesperada del servidor';
        }
      },
      error: (err) => {
        console.error('❌ Error en login:', err); 
        this.isLoading = false;
        
        if (err.status === 401) {
          this.errorMessage = 'Usuario o contraseña incorrectos';
        } else if (err.status === 400) {
          this.errorMessage = err.error?.error || 'Datos inválidos';
        } else if (err.status === 500) {
          this.errorMessage = 'Error interno del servidor';
        } else {
          this.errorMessage = 'Error de conexión. Intenta nuevamente.';
        }
      }
    });
  }

  private handleOtpVerification(): void {
    if (!this.otp?.trim()) {
      this.errorMessage = 'Código OTP requerido';
      this.isLoading = false;
      return;
    }

    if (!/^\d{6}$/.test(this.otp)) {
      this.errorMessage = 'El código OTP debe tener 6 dígitos numéricos';
      this.isLoading = false;
      return;
    }

    console.log('🔑 Verificando OTP...', {
      otp: this.otp,
      tempToken: this.tempToken ? 'Presente' : 'Ausente'
    });

    this.authService.verifyOtp(this.otp, this.tempToken).subscribe({
      next: (res) => {
        console.log('✅ OTP verificado correctamente:', res);
        this.isLoading = false;
        
        if (res.token) {
          localStorage.setItem('token', res.token);
          this.router.navigate(['/tasks']);
        } else {
          this.errorMessage = 'No se recibió token de autenticación';
        }
      },
      error: (err) => {
        console.error('❌ Error en verificación OTP:', err);
        this.isLoading = false;
        
        if (err.status === 401) {
          if (err.error?.error?.includes('Token expirado')) {
            this.errorMessage = 'Token expirado. Vuelve a iniciar sesión.';
            this.resetToCredentials();
          } else {
            this.errorMessage = 'Código OTP incorrecto';
          }
        } else if (err.status === 400) {
          this.errorMessage = err.error?.error || 'Datos inválidos';
        } else {
          this.errorMessage = 'Error de verificación. Intenta nuevamente.';
        }
      }
    });
  }

  resetToCredentials(): void {
    this.step = 'credentials';
    this.otp = '';
    this.tempToken = '';
    this.errorMessage = '';
    this.isLoading = false;
  }

  clearError(): void {
    this.errorMessage = '';
  }
}
