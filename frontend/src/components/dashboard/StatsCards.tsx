import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Order } from '@/types';
import { Activity, CheckCircle, Clock, AlertTriangle } from 'lucide-react';

interface Props {
  orders: Order[];
}

export function StatsCards({ orders }: Props) {
  const total = orders.length;
  const active = orders.filter(o => o.status === 'in_progress').length;
  const completed = orders.filter(o => o.status === 'completed').length;
  const failed = orders.filter(o => o.status === 'failed').length;

  const stats = [
    { label: 'Total Orders', value: total, icon: Activity, color: 'text-primary' },
    { label: 'Active', value: active, icon: Clock, color: 'text-accent-foreground' },
    { label: 'Completed', value: completed, icon: CheckCircle, color: 'text-primary' },
    { label: 'Failed', value: failed, icon: AlertTriangle, color: 'text-destructive' },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map(s => (
        <Card key={s.label}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{s.label}</CardTitle>
            <s.icon className={`h-4 w-4 ${s.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{s.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
