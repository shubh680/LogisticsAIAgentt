import { Layout } from '@/components/Layout';
import { StatsSummary } from '@/components/performance/StatsSummary';
import { PerformanceCharts } from '@/components/performance/PerformanceCharts';
import { usePerformance } from '@/hooks/usePerformance';
import { Skeleton } from '@/components/ui/skeleton';

const Performance = () => {
  const { data, isLoading } = usePerformance();

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Agent Performance</h1>
          <p className="text-muted-foreground">Analytics and insights on AI agent operations</p>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-4">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
            </div>
            <Skeleton className="h-64" />
          </div>
        ) : data ? (
          <>
            <StatsSummary data={data} />
            <PerformanceCharts data={data} />
          </>
        ) : null}
      </div>
    </Layout>
  );
};

export default Performance;
