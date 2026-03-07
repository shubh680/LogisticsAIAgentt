import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { mockHumanReviewItems } from '@/data/mockData';
import { HumanReviewItem, ReviewStatus } from '@/types';

const fetchReviewItems = async (): Promise<HumanReviewItem[]> => {
  await new Promise(r => setTimeout(r, 300));
  return mockHumanReviewItems;
};

export const useHumanReview = () => useQuery({ queryKey: ['humanReview'], queryFn: fetchReviewItems });

export const useReviewAction = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: ReviewStatus }) => {
      // Replace with Firebase update
      await new Promise(r => setTimeout(r, 300));
      return { id, status };
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['humanReview'] }),
  });
};
