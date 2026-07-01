import axios from 'axios';
import { HealthResponse, DiagnosisResponse } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const checkHealth = async (): Promise<HealthResponse> => {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
};

export const runInvestigation = async (userId: string): Promise<DiagnosisResponse> => {
  const response = await apiClient.post<DiagnosisResponse>('/api/investigate', {
    user_id: userId,
    namespace: 'default',
  });
  return response.data;
};

export const getContexts = async (): Promise<{ contexts: string[]; current_context: string | null }> => {
  const response = await apiClient.get('/api/kubernetes/contexts');
  return response.data;
};

export const selectContext = async (context: string): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post('/api/kubernetes/contexts/select', { context });
  return response.data;
};
