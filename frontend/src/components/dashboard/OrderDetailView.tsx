import { Order } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Brain, Zap, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

const actionTypeColors: Record<string, string> = {
  email_sent: 'bg-primary/20 text-primary',
  data_updated: 'bg-secondary text-secondary-foreground',
  api_call: 'bg-accent text-accent-foreground',
  verification: 'bg-muted text-muted-foreground',
  escalated: 'bg-destructive/20 text-destructive',
  notification: 'bg-primary/10 text-primary',
};

export function OrderDetailView({ order }: { order: Order }) {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">{order.title}</h1>
          <p className="text-muted-foreground">{order.description}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Order ID</CardTitle></CardHeader>
          <CardContent><span className="font-mono">{order.id}</span></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Agent</CardTitle></CardHeader>
          <CardContent>{order.agentName}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Status</CardTitle></CardHeader>
          <CardContent><Badge>{order.status.replace('_', ' ')}</Badge></CardContent>
        </Card>
      </div>

      {/* Input / Output */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-sm flex items-center gap-2">Input Data</CardTitle></CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-3 rounded-md overflow-auto">{JSON.stringify(order.inputData, null, 2)}</pre>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm flex items-center gap-2">Output Data</CardTitle></CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-3 rounded-md overflow-auto">{JSON.stringify(order.outputData, null, 2)}</pre>
          </CardContent>
        </Card>
      </div>

      {/* Thought Process */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Brain className="h-5 w-5 text-primary" /> Agent Thought Process</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {order.thoughts.map((t, i) => (
            <div key={t.id} className="relative pl-6 pb-4">
              {i < order.thoughts.length - 1 && <div className="absolute left-[11px] top-6 bottom-0 w-px bg-border" />}
              <div className="absolute left-0 top-1 h-6 w-6 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary">{i + 1}</div>
              <div className="bg-muted/50 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <p className="font-medium text-sm">{t.thought}</p>
                  <span className="text-xs text-muted-foreground whitespace-nowrap ml-2">{new Date(t.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-sm text-muted-foreground mb-2">{t.reasoning}</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Confidence:</span>
                  <Progress value={t.confidence * 100} className="h-2 w-24" />
                  <span className="text-xs font-medium">{(t.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Zap className="h-5 w-5 text-primary" /> Actions Taken</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {order.actions.map(a => (
            <div key={a.id} className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${actionTypeColors[a.type] || 'bg-muted text-muted-foreground'}`}>
                    {a.type.replace('_', ' ')}
                  </span>
                  <span className="font-medium text-sm">{a.description}</span>
                </div>
                <Badge variant={a.status === 'completed' ? 'default' : a.status === 'failed' ? 'destructive' : 'secondary'}>
                  {a.status}
                </Badge>
              </div>
              <div className="grid gap-2 md:grid-cols-2 mt-3">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Input</p>
                  <pre className="text-xs bg-muted p-2 rounded overflow-auto">{JSON.stringify(a.input, null, 2)}</pre>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Output</p>
                  <pre className="text-xs bg-muted p-2 rounded overflow-auto">{JSON.stringify(a.output, null, 2)}</pre>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-muted-foreground">Confidence:</span>
                <Progress value={a.confidence * 100} className="h-2 w-24" />
                <span className="text-xs font-medium">{(a.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
