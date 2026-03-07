import { useParams } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { OrderDetailView } from '@/components/dashboard/OrderDetailView';
import { useOrder } from '@/hooks/useOrders';
import { Skeleton } from '@/components/ui/skeleton';

const OrderDetail = () => {
  const { orderId } = useParams<{ orderId: string }>();
  const { data: order, isLoading } = useOrder(orderId || '');

  return (
    <Layout>
      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-48" />
          <Skeleton className="h-64" />
        </div>
      ) : order ? (
        <OrderDetailView order={order} />
      ) : (
        <p className="text-muted-foreground">Order not found.</p>
      )}
    </Layout>
  );
};

export default OrderDetail;
