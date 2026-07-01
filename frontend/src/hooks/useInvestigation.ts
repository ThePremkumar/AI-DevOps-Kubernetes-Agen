import { useMutation, useQuery } from '@tanstack/react-query';
import { checkHealth, runInvestigation } from '../services/api';

export const useHealthQuery = () => {
  return useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 10000, // Poll every 10 seconds
  });
};

export const useInvestigationMutation = () => {
  return useMutation({
    mutationFn: runInvestigation,
  });
};
