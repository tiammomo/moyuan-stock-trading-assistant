import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getWatchlist,
  resolveWatchStock,
  createWatchItem,
  updateWatchItem,
  deleteWatchItem,
} from "@/lib/api";
import type {
  WatchItemCreate,
  WatchItemUpdate,
  WatchStockResolveRequest,
} from "@/types/watchlist";

export function useWatchlist() {
  const queryClient = useQueryClient();

  const watchlistQuery = useQuery({
    queryKey: ["watchlist"],
    queryFn: getWatchlist,
  });

  const createMutation = useMutation({
    mutationFn: (data: WatchItemCreate) => createWatchItem(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: (data: WatchStockResolveRequest) => resolveWatchStock(data),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: WatchItemUpdate }) =>
      updateWatchItem(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteWatchItem(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  return {
    watchlist: watchlistQuery.data ?? [],
    isLoading: watchlistQuery.isLoading,
    isError: watchlistQuery.isError,
    createItem: createMutation.mutate,
    createItemAsync: createMutation.mutateAsync,
    updateItem: updateMutation.mutate,
    updateItemAsync: updateMutation.mutateAsync,
    deleteItem: deleteMutation.mutate,
    resolveStock: resolveMutation.mutate,
    resolveStockAsync: resolveMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isResolving: resolveMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
