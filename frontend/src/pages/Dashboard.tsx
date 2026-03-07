import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { StatsCards } from '@/components/dashboard/StatsCards';
import { OrdersTable } from '@/components/dashboard/OrdersTable';
import { useOrders } from '@/hooks/useOrders';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useQueryClient } from '@tanstack/react-query';

const Dashboard = () => {
  const { data: orders, isLoading } = useOrders();
  const qc = useQueryClient();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzedCount, setAnalyzedCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  // Poll analysis status while a run is in progress
  useEffect(() => {
    if (!isAnalyzing) return;
    const interval = setInterval(async () => {
      const res = await fetch('/api/analyze/status');
      if (!res.ok) return;
      const data = await res.json();
      setAnalyzedCount(data.analyzed_count);
      if (data.total_count) setTotalCount(data.total_count);
      // Refresh orders incrementally while analysis runs
      qc.invalidateQueries({ queryKey: ['orders'] });
      if (!data.is_analyzing) {
        setIsAnalyzing(false);
        clearInterval(interval);
        qc.invalidateQueries({ queryKey: ['orders'] });
        qc.invalidateQueries({ queryKey: ['performance'] });
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [isAnalyzing, qc]);

  const handleAnalyze = async () => {
    const res = await fetch('/api/analyze', { method: 'POST' });
    if (res.ok) setIsAnalyzing(true);
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground">Live tracking of AI agent operations</p>
          </div>
          <div className="flex items-center gap-3">
            {isAnalyzing && (
              <Badge variant="secondary" className="animate-pulse">
                Analyzing… {analyzedCount}{totalCount ? `/${totalCount}` : ''} shipments
              </Badge>
            )}
            <Button onClick={handleAnalyze} disabled={isAnalyzing} size="sm">
              {isAnalyzing ? 'Running Analysis…' : 'Run Risk Analysis'}
            </Button>
          </div>
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
                <CardTitle className="text-lg">Shipments</CardTitle>
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
