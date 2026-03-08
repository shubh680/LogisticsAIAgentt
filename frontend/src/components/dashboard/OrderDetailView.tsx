import { Order } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Brain, Zap, ArrowLeft, GitBranch, CheckCircle2, XCircle, SkipForward } from 'lucide-react';
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

type JsonLike = Record<string, unknown> | unknown[] | string | number | boolean | null | undefined;

const formatKey = (key: string) =>
  key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/^./, c => c.toUpperCase());

function PrimitiveValue({ value }: { value: JsonLike }) {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground">-</span>;
  }
  if (typeof value === 'boolean') {
    return <span className={value ? 'text-green-600 font-medium' : 'text-destructive font-medium'}>{value ? 'True' : 'False'}</span>;
  }
  if (typeof value === 'number') {
    return <span className="font-medium tabular-nums">{value}</span>;
  }
  return <span className="break-words">{String(value)}</span>;
}

function DataRenderer({ data, level = 0 }: { data: JsonLike; level?: number }) {
  if (data === null || data === undefined) {
    return <PrimitiveValue value={data} />;
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <span className="text-muted-foreground">No items</span>;
    }
    return (
      <div className="space-y-2">
        {data.map((item, idx) => (
          <div key={`${level}-arr-${idx}`} className="rounded-md border bg-background/70 p-2">
            <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Item {idx + 1}</p>
            <DataRenderer data={item as JsonLike} level={level + 1} />
          </div>
        ))}
      </div>
    );
  }

  if (typeof data === 'object') {
    const entries = Object.entries(data as Record<string, unknown>);
    if (entries.length === 0) {
      return <span className="text-muted-foreground">No data</span>;
    }

    return (
      <div className="space-y-2">
        {entries.map(([key, value]) => {
          const isNested = value !== null && typeof value === 'object';
          return (
            <div key={`${level}-${key}`} className="rounded-md border bg-background/70 p-2">
              <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{formatKey(key)}</p>
              {isNested ? <DataRenderer data={value as JsonLike} level={level + 1} /> : <PrimitiveValue value={value as JsonLike} />}
            </div>
          );
        })}
      </div>
    );
  }

  return <PrimitiveValue value={data} />;
}

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
            <div className="max-h-80 overflow-auto rounded-md bg-muted/40 p-3 text-xs">
              <DataRenderer data={order.inputData} />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm flex items-center gap-2">Output Data</CardTitle></CardHeader>
          <CardContent>
            <div className="max-h-80 overflow-auto rounded-md bg-muted/40 p-3 text-xs">
              <DataRenderer data={order.outputData} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Trace */}
      {order.pipelineSteps && order.pipelineSteps.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5 text-primary" /> Agent Pipeline Trace
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative">
              {order.pipelineSteps.map((step, i) => {
                const isLast = i === order.pipelineSteps!.length - 1;
                const StatusIcon =
                  step.status === 'completed' ? CheckCircle2 :
                  step.status === 'failed' ? XCircle : SkipForward;
                const iconColor =
                  step.status === 'completed' ? 'text-green-500' :
                  step.status === 'failed' ? 'text-destructive' : 'text-muted-foreground';
                return (
                  <div key={step.id} className="flex gap-4 mb-4">
                    {/* Connector */}
                    <div className="flex flex-col items-center">
                      <StatusIcon className={`h-6 w-6 mt-1 shrink-0 ${iconColor}`} />
                      {!isLast && <div className="w-px flex-1 bg-border mt-1" />}
                    </div>
                    {/* Content */}
                    <div className={`flex-1 rounded-lg border p-4 mb-${isLast ? '0' : '0'}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-sm">{step.agentName}</span>
                        <Badge variant={step.status === 'completed' ? 'default' : step.status === 'failed' ? 'destructive' : 'secondary'}>
                          {step.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">{step.summary}</p>
                      <div className="grid gap-2 md:grid-cols-2">
                        <div>
                          <p className="text-xs text-muted-foreground mb-1 font-medium">Input</p>
                          <div className="max-h-32 overflow-auto rounded bg-muted/40 p-2 text-xs">
                            <DataRenderer data={step.input} />
                          </div>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground mb-1 font-medium">Output</p>
                          <div className="max-h-32 overflow-auto rounded bg-muted/40 p-2 text-xs">
                            <DataRenderer data={step.output} />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

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
                  <div className="max-h-40 overflow-auto rounded bg-muted/40 p-2 text-xs">
                    <DataRenderer data={a.input} />
                  </div>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Output</p>
                  <div className="max-h-40 overflow-auto rounded bg-muted/40 p-2 text-xs">
                    <DataRenderer data={a.output} />
                  </div>
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
