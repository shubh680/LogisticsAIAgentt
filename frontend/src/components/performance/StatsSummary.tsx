import { PerformanceData } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, Users, Clock, Target } from 'lucide-react';

export function StatsSummary({ data }: { data: PerformanceData }) {
  const stats = [
    { label: 'Total Orders', value: data.totalOrders.toLocaleString(), icon: TrendingUp },
    { label: 'Auto-Complete Rate', value: `${((data.autoCompleted / data.totalOrders) * 100).toFixed(1)}%`, icon: Target },
    { label: 'Human Reviews', value: data.humanInLoop.toLocaleString(), icon: Users },
    { label: 'Avg Processing Time', value: `${data.avgProcessingTime}min`, icon: Clock },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map(s => (
        <Card key={s.label}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{s.label}</CardTitle>
            <s.icon className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{s.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
