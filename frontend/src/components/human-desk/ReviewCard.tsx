import { HumanReviewItem } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { CheckCircle, XCircle } from 'lucide-react';

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

export function ReviewCard({ item, onApprove, onReject }: Props) {
  const confidenceColor = item.confidence >= 0.8 ? 'text-primary' : item.confidence >= 0.5 ? 'text-accent-foreground' : 'text-destructive';

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
        <div>
          <p className="text-xs text-muted-foreground mb-1">Action</p>
          <p className="text-sm">{item.action.description}</p>
          <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground mt-1 inline-block">
            {item.action.type.replace('_', ' ')}
          </span>
        </div>

        <div>
          <p className="text-xs text-muted-foreground mb-1">Agent Reasoning</p>
          <p className="text-sm bg-muted/50 p-3 rounded-md">{item.agentReasoning}</p>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-muted-foreground">Confidence Level</p>
            <span className={`text-sm font-bold ${confidenceColor}`}>{(item.confidence * 100).toFixed(0)}%</span>
          </div>
          <Progress value={item.confidence * 100} className="h-3" />
        </div>

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
            Reviewed by {item.reviewedBy} on {new Date(item.reviewedAt).toLocaleString()}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
