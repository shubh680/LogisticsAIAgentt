import { useQuery } from '@tanstack/react-query';
import { PerformanceData } from '@/types';

const fetchPerformance = async (): Promise<PerformanceData> => {
  const res = await fetch('/api/performance');
  if (!res.ok) throw new Error('Failed to fetch performance data');
  return res.json();
};

export const usePerformance = () =>
  useQuery({ queryKey: ['performance'], queryFn: fetchPerformance, refetchInterval: 30_000 });
