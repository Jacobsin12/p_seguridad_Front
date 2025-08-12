// logs.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

interface LogsStats {
  total_requests: number;
  status_counts: { [statusCode: string]: number };
  avg_response_time: number;
  endpoints: { [path: string]: { hits: number; avg_time: number } };
}

@Injectable({
  providedIn: 'root',
})
export class LogsService {
  private apiUrl = 'https://gateway-sktd.onrender.com/api/logs/stats'; // URL correcta del endpoint

  constructor(private http: HttpClient) {}

  getLogsStats(): Observable<LogsStats> {
    return this.http.get<LogsStats>(this.apiUrl);
  }
}
