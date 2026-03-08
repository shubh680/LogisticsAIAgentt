import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { HumanReviewItem, ReviewStatus } from '@/types';
import { API_BASE } from '@/lib/api';

const fetchReviewItems = async (): Promise<HumanReviewItem[]> => {
  const res = await fetch(`${API_BASE}/api/reviews`);
  if (!res.ok) throw new Error('Failed to fetch reviews');
  return res.json();
};

export const useHumanReview = () =>
  useQuery({ queryKey: ['humanReview'], queryFn: fetchReviewItems, refetchInterval: 30_000 });

export const useReviewAction = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: ReviewStatus }) => {
      const res = await fetch(`${API_BASE}/api/reviews/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error('Failed to update review');
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['humanReview'] }),
  });
};
