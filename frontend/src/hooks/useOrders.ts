import { useQuery } from '@tanstack/react-query';
import { Order } from '@/types';

const fetchOrders = async (): Promise<Order[]> => {
  const res = await fetch('/api/shipments');
  if (!res.ok) throw new Error('Failed to fetch shipments');
  return res.json();
};

const fetchOrderById = async (id: string): Promise<Order | undefined> => {
  const res = await fetch(`/api/shipments/${id}`);
  if (res.status === 404) return undefined;
  if (!res.ok) throw new Error('Failed to fetch shipment');
  return res.json();
};

export const useOrders = () =>
  useQuery({ queryKey: ['orders'], queryFn: fetchOrders, refetchInterval: 30_000 });
export const useOrder = (id: string) =>
  useQuery({ queryKey: ['order', id], queryFn: () => fetchOrderById(id), enabled: !!id });
