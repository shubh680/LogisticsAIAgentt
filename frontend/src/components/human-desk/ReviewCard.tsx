import { HumanReviewItem } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { CheckCircle, XCircle, Truck, CloudSun, AlertTriangle, Clock, BarChart2, ArrowRight } from 'lucide-react';

interface Props {
  item: HumanReviewItem;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

const statusVariant: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pending: 'outline',
  approved: 'default',
  rejected: 'destructive',
};

const riskBadgeVariant = (level?: string): 'default' | 'secondary' | 'destructive' | 'outline' => {
  if (level === 'high') return 'destructive';
  if (level === 'medium') return 'secondary';
  return 'outline';
};

export function ReviewCard({ item, onApprove, onReject }: Props) {
  const confidenceColor = item.confidence >= 0.8 ? 'text-primary' : item.confidence >= 0.5 ? 'text-accent-foreground' : 'text-destructive';
  const d = item.shipmentDetails;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{item.orderTitle}</CardTitle>
          <Badge variant={statusVariant[item.status]}>{item.status}</Badge>
        </div>
        <p className="text-xs text-muted-foreground font-mono">{item.orderId} · {item.id}</p>
      </CardHeader>
      <CardContent className="space-y-4">

        {/* ── Shipment snapshot ── */}
        {d && (
          <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Shipment Details</p>

            {/* Row 1: carrier + weather + priority */}
            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground flex items-center gap-1"><Truck className="h-3 w-3" /> Carrier</span>
                <span className="text-sm font-medium">{d.carrier ?? '—'}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground flex items-center gap-1"><CloudSun className="h-3 w-3" /> Weather</span>
                <span className="text-sm font-medium">{d.weather ?? '—'}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">Priority</span>
                <Badge variant={d.priority === 'High' ? 'destructive' : d.priority === 'Medium' ? 'secondary' : 'outline'} className="w-fit text-xs">
                  {d.priority ?? '—'}
                </Badge>
              </div>
            </div>

            <Separator />

            {/* Row 2: ETA + warehouse + traffic */}
            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground flex items-center gap-1"><Clock className="h-3 w-3" /> ETA</span>
                <span className="text-sm font-medium">
                  {d.etaHours != null ? `${d.etaHours.toFixed(1)} hrs` : '—'}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground flex items-center gap-1"><BarChart2 className="h-3 w-3" /> Warehouse Load</span>
                <span className="text-sm font-medium">{d.warehouseLoad != null ? `${d.warehouseLoad}%` : '—'}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">Traffic Congestion</span>
                <span className="text-sm font-medium">{d.trafficDelay != null ? `${d.trafficDelay}%` : '—'}</span>
              </div>
            </div>

            <Separator />

            {/* Row 3: ML delay prob + risk level + overdue */}
            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">Delay Probability</span>
                <span className="text-sm font-medium">{d.delayProbability != null ? `${d.delayProbability}%` : '—'}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">Risk Level</span>
                <Badge variant={riskBadgeVariant(d.riskLevel)} className="w-fit text-xs capitalize">
                  {d.riskLevel ?? '—'}
                </Badge>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> Overdue</span>
                <span className={`text-sm font-medium ${d.isDelayed ? 'text-destructive' : 'text-green-600'}`}>
                  {d.isDelayed ? 'Yes' : 'No'}
                </span>
              </div>
            </div>

            {/* Root causes */}
            {d.rootCauses && d.rootCauses.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Root Causes Identified</p>
                <div className="flex flex-wrap gap-1">
                  {d.rootCauses.map((c, i) => (
                    <span key={i} className="text-xs bg-destructive/10 text-destructive px-2 py-0.5 rounded-full">{c}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Triggered policy rules */}
            {d.triggeredRules && d.triggeredRules.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Why This Needs Review</p>
                <ul className="space-y-1">
                  {d.triggeredRules.map((r, i) => (
                    <li key={i} className="flex items-start gap-1 text-xs">
                      <ArrowRight className="h-3 w-3 mt-0.5 text-muted-foreground shrink-0" />
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* ── Recommended action ── */}
        <div>
          <p className="text-xs text-muted-foreground mb-1">Recommended Action</p>
          <p className="text-sm font-medium">{item.action.description}</p>
        </div>

        {/* ── Agent reasoning ── */}
        <div>
          <p className="text-xs text-muted-foreground mb-1">Why the AI flagged this</p>
          <p className="text-sm bg-muted/50 p-3 rounded-md leading-relaxed">{item.agentReasoning}</p>
        </div>

        {/* ── Confidence ── */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-muted-foreground">AI Confidence</p>
            <span className={`text-sm font-bold ${confidenceColor}`}>{(item.confidence * 100).toFixed(0)}%</span>
          </div>
          <Progress value={item.confidence * 100} className="h-3" />
        </div>

        {/* ── Actions ── */}
        {item.status === 'pending' && (
          <div className="flex gap-2 pt-2">
            <Button className="flex-1" onClick={() => onApprove(item.id)}>
              <CheckCircle className="h-4 w-4 mr-1" /> Approve
            </Button>
            <Button variant="destructive" className="flex-1" onClick={() => onReject(item.id)}>
              <XCircle className="h-4 w-4 mr-1" /> Reject
            </Button>
          </div>
        )}

        {item.reviewedAt && (
          <p className="text-xs text-muted-foreground">
            Reviewed on {new Date(item.reviewedAt).toLocaleString()}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
