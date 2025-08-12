export interface Task {
  id: number;
  name: string;
  description: string;
  create_at: string;
  deadline: string;
  status: 'InProgress' | 'Revision' | 'Completed' | 'Paused';
  isAlive: boolean;
}