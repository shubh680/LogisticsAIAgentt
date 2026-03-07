import { PerformanceData } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  LineChart, Line, ResponsiveContainer, Legend,
} from 'recharts';

const COLORS = ['hsl(222, 47%, 11%)', 'hsl(210, 40%, 96%)', 'hsl(0, 84%, 60%)'];

export function PerformanceCharts({ data }: { data: PerformanceData }) {
  const pieData = [
    { name: 'Auto-Completed', value: data.autoCompleted },
    { name: 'Human-in-Loop', value: data.humanInLoop },
    { name: 'Failed', value: data.failedOrders },
  ];

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Completion Breakdown */}
      <Card>
        <CardHeader><CardTitle className="text-sm">Completion Breakdown</CardTitle></CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Action Types */}
      <Card>
        <CardHeader><CardTitle className="text-sm">Action Types</CardTitle></CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.actionBreakdown}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="type" tick={{ fontSize: 11 }} tickFormatter={v => v.replace('_', ' ')} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="hsl(222, 47%, 11%)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Daily Performance */}
      <Card className="md:col-span-2">
        <CardHeader><CardTitle className="text-sm">Daily Performance</CardTitle></CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.dailyPerformance}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="completed" stroke="hsl(222, 47%, 11%)" strokeWidth={2} />
              <Line type="monotone" dataKey="failed" stroke="hsl(0, 84%, 60%)" strokeWidth={2} />
              <Line type="monotone" dataKey="humanReview" stroke="hsl(210, 40%, 60%)" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Confidence Distribution */}
      <Card className="md:col-span-2">
        <CardHeader><CardTitle className="text-sm">Confidence Distribution</CardTitle></CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.confidenceDistribution}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="range" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="hsl(210, 40%, 60%)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
