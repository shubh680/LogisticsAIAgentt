import { useState } from 'react';
import { Layout } from '@/components/Layout';
import { ReviewCard } from '@/components/human-desk/ReviewCard';
import { useHumanReview, useReviewAction } from '@/hooks/useHumanReview';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';

const HumanDesk = () => {
  const { data: items, isLoading } = useHumanReview();
  const reviewAction = useReviewAction();
  const { toast } = useToast();

  const handleApprove = (id: string) => {
    reviewAction.mutate({ id, status: 'approved' }, {
      onSuccess: () => toast({ title: 'Action approved', description: `Review ${id} has been approved.` }),
    });
  };

  const handleReject = (id: string) => {
    reviewAction.mutate({ id, status: 'rejected' }, {
      onSuccess: () => toast({ title: 'Action rejected', description: `Review ${id} has been rejected.`, variant: 'destructive' }),
    });
  };

  const pending = items?.filter(i => i.status === 'pending') || [];
  const reviewed = items?.filter(i => i.status !== 'pending') || [];

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Human Desk</h1>
          <p className="text-muted-foreground">Review and approve AI agent actions</p>
        </div>

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2">
            {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-64" />)}
          </div>
        ) : (
          <Tabs defaultValue="pending">
            <TabsList>
              <TabsTrigger value="pending">Pending ({pending.length})</TabsTrigger>
              <TabsTrigger value="reviewed">Reviewed ({reviewed.length})</TabsTrigger>
            </TabsList>
            <TabsContent value="pending" className="mt-4">
              <div className="grid gap-4 md:grid-cols-2">
                {pending.map(item => (
                  <ReviewCard key={item.id} item={item} onApprove={handleApprove} onReject={handleReject} />
                ))}
                {pending.length === 0 && <p className="text-muted-foreground col-span-2">No pending reviews.</p>}
              </div>
            </TabsContent>
            <TabsContent value="reviewed" className="mt-4">
              <div className="grid gap-4 md:grid-cols-2">
                {reviewed.map(item => (
                  <ReviewCard key={item.id} item={item} onApprove={handleApprove} onReject={handleReject} />
                ))}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Layout>
  );
};

export default HumanDesk;
