import { useQuery } from '@tanstack/react-query';
import { mockOrders } from '@/data/mockData';
import { Order } from '@/types';

const fetchOrders = async (): Promise<Order[]> => {
  // Replace with Firebase call: const snapshot = await getDocs(collection(db, 'orders'));
  await new Promise(r => setTimeout(r, 300));
  return mockOrders;
};

const fetchOrderById = async (id: string): Promise<Order | undefined> => {
  await new Promise(r => setTimeout(r, 200));
  return mockOrders.find(o => o.id === id);
};

export const useOrders = () => useQuery({ queryKey: ['orders'], queryFn: fetchOrders });
export const useOrder = (id: string) => useQuery({ queryKey: ['order', id], queryFn: () => fetchOrderById(id) });
