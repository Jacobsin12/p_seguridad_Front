import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';

import { ChartModule } from 'primeng/chart';
import { TableModule } from 'primeng/table';

import { LogsService } from '../logs.service';

@Component({
  selector: 'app-log-list',
  standalone: true,
  imports: [
    CommonModule,
    ChartModule,
    TableModule
  ],
  templateUrl: './log-list.component.html',
  styleUrls: ['./log-list.component.css'] // si tienes estilos
})
export class LogListComponent implements OnInit {
  totalRequests = 0;
  status200 = 0;
  status404 = 0;
  status500 = 0;
  avgResponseTime = 0;

  endpoints: { path: string; hits: number; avg_time: number }[] = [];

  data: any;
  options: any;

  error = '';

  constructor(private logsService: LogsService) {}

  ngOnInit(): void {
    this.logsService.getLogsStats().subscribe(
      (data) => {
        this.totalRequests = data.total_requests;
        this.status200 = data.status_counts['200'] || 0;
        this.status404 = data.status_counts['404'] || 0;
        this.status500 = data.status_counts['500'] || 0;
        this.avgResponseTime = data.avg_response_time;

        // Convertir el objeto endpoints a array para la tabla
        this.endpoints = Object.entries(data.endpoints).map(([path, info]) => ({
          path,
          hits: info.hits,
          avg_time: info.avg_time
        }));

        this.prepareChartData(data.endpoints);
      },
      (err) => {
        this.error = 'Error al cargar datos';
        console.error(err);
      }
    );
  }

  prepareChartData(endpoints: any): void {
    const labels = Object.keys(endpoints);
    const hits = labels.map(label => endpoints[label].hits);

    this.data = {
      labels,
      datasets: [
        {
          label: 'Número de Hits por Endpoint',
          backgroundColor: [
            '#FF6384',
            '#36A2EB',
            '#FFCE56',
            '#4BC0C0',
            '#9966FF',
            '#FF9F40',
            '#8AFF33',
            '#FF33F6',
            '#33FFF2',
            '#F27333'
          ],
          data: hits
        }
      ]
    };

    this.options = {
      responsive: true,
      plugins: {
        legend: {
          position: 'top'
        },
        title: {
          display: true,
          text: 'Uso de Endpoints'
        }
      }
    };
  }
}
