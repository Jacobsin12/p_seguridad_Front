import { CommonModule } from '@angular/common';
import { Component, Renderer2 } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';

import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputGroupModule } from 'primeng/inputgroup';
import { InputGroupAddonModule } from 'primeng/inputgroupaddon';
import { InputTextModule } from 'primeng/inputtext';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    InputTextModule,
    InputGroupModule,
    InputGroupAddonModule,
    ButtonModule,
    CardModule
  ],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css']
})
export class RegisterComponent {
  // Datos del formulario
  username: string = '';
  password: string = '';
  confirmPassword: string = '';
  email: string = '';
  birthdate: string | Date = '';
  secret_question: string = '';
  secret_answer: string = '';

  // Estado del componente
  errorMessage: string = '';
  qrCodeUrl: string = '';
  showQr: boolean = false;
  darkMode: boolean = false;

  constructor(
    private authService: AuthService,
    private router: Router,
    private renderer: Renderer2
  ) {
    // Cargar modo oscuro desde localStorage
    const savedMode = localStorage.getItem('darkMode');
    this.darkMode = savedMode ? JSON.parse(savedMode) : false;
  }

  toggleDarkMode(): void {
    this.darkMode = !this.darkMode;
    // Guardar modo oscuro en localStorage para persistencia
    localStorage.setItem('darkMode', String(this.darkMode));
    console.log('Dark mode:', this.darkMode); // Depuración
  }

  onRegister(): void {
    // Validar que las contraseñas coincidan
    if (this.password !== this.confirmPassword) {
      this.errorMessage = 'Las contraseñas no coinciden.';
      return;
    }

    // Preparar los datos
    const formattedBirthdate =
      typeof this.birthdate === 'string'
        ? this.birthdate
        : this.birthdate?.toISOString().split('T')[0];

    const data = {
      username: this.username,
      password: this.password,
      email: this.email,
      birthdate: formattedBirthdate,
      secret_question: this.secret_question,
      secret_answer: this.secret_answer
    };

    // Llamar al servicio de registro
    this.authService.register(data).subscribe({
      next: (res) => {
        console.log('✅ Usuario registrado:', res);
        if (res.qrCodeUrl) {
          this.qrCodeUrl = res.qrCodeUrl;
          this.showQr = true;
        } else {
          this.router.navigate(['/auth/login']);
        }
      },
      error: (err) => {
        this.errorMessage = err.error?.error || 'Error al registrar usuario.';
      }
    });
  }
}