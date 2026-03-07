import { useQuery } from '@tanstack/react-query';
import { mockPerformanceData } from '@/data/mockData';
import { PerformanceData } from '@/types';

const fetchPerformance = async (): Promise<PerformanceData> => {
  await new Promise(r => setTimeout(r, 300));
  return mockPerformanceData;
};

export const usePerformance = () => useQuery({ queryKey: ['performance'], queryFn: fetchPerformance });
