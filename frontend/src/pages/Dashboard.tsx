import { Layout } from '@/components/Layout';
import { StatsCards } from '@/components/dashboard/StatsCards';
import { OrdersTable } from '@/components/dashboard/OrdersTable';
import { useOrders } from '@/hooks/useOrders';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

const Dashboard = () => {
  const { data: orders, isLoading } = useOrders();

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Live tracking of AI agent operations</p>
        </div>

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-4">
            {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
          </div>
        ) : orders ? (
          <>
            <StatsCards orders={orders} />
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Orders</CardTitle>
              </CardHeader>
              <CardContent>
                <OrdersTable orders={orders} />
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>
    </Layout>
  );
};

export default Dashboard;
