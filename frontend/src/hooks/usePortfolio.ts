import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createPortfolioAccount,
  createPortfolioPosition,
  deletePortfolioAccount,
  deletePortfolioPosition,
  getPortfolioSummary,
  importPortfolioScreenshot,
  updatePortfolioAccount,
  updatePortfolioPosition,
} from "@/lib/api";
import type {
  PortfolioAccountCreate,
  PortfolioAccountUpdate,
  PortfolioPositionCreate,
  PortfolioSummary,
  PortfolioPositionUpdate,
  PortfolioScreenshotImportRequest,
} from "@/types/portfolio";

export function usePortfolio() {
  const queryClient = useQueryClient();

  const summaryQuery = useQuery({
    queryKey: ["portfolio", "summary"],
    queryFn: getPortfolioSummary,
    refetchInterval: (query) => {
      const summary = query.state.data as PortfolioSummary | undefined;
      return summary?.market_schedule?.next_refresh_in_ms ?? 60_000;
    },
    refetchIntervalInBackground: true,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["portfolio"] });
  };

  const createAccountMutation = useMutation({
    mutationFn: (data: PortfolioAccountCreate) => createPortfolioAccount(data),
    onSuccess: invalidate,
  });

  const updateAccountMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: PortfolioAccountUpdate }) =>
      updatePortfolioAccount(id, data),
    onSuccess: invalidate,
  });

  const deleteAccountMutation = useMutation({
    mutationFn: (id: string) => deletePortfolioAccount(id),
    onSuccess: invalidate,
  });

  const createPositionMutation = useMutation({
    mutationFn: (data: PortfolioPositionCreate) => createPortfolioPosition(data),
    onSuccess: invalidate,
  });

  const updatePositionMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: PortfolioPositionUpdate }) =>
      updatePortfolioPosition(id, data),
    onSuccess: invalidate,
  });

  const deletePositionMutation = useMutation({
    mutationFn: (id: string) => deletePortfolioPosition(id),
    onSuccess: invalidate,
  });

  const importScreenshotMutation = useMutation({
    mutationFn: (data: PortfolioScreenshotImportRequest) => importPortfolioScreenshot(data),
    onSuccess: invalidate,
  });

  return {
    summary: summaryQuery.data ?? null,
    isLoading: summaryQuery.isLoading,
    summaryUpdatedAt: summaryQuery.dataUpdatedAt,
    refetch: summaryQuery.refetch,
    createAccountAsync: createAccountMutation.mutateAsync,
    updateAccountAsync: updateAccountMutation.mutateAsync,
    deleteAccountAsync: deleteAccountMutation.mutateAsync,
    createPositionAsync: createPositionMutation.mutateAsync,
    updatePositionAsync: updatePositionMutation.mutateAsync,
    deletePositionAsync: deletePositionMutation.mutateAsync,
    importScreenshotAsync: importScreenshotMutation.mutateAsync,
    isMutating:
      createAccountMutation.isPending ||
      updateAccountMutation.isPending ||
      deleteAccountMutation.isPending ||
      createPositionMutation.isPending ||
      updatePositionMutation.isPending ||
      deletePositionMutation.isPending ||
      importScreenshotMutation.isPending,
  };
}
