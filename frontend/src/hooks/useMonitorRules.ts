"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createWatchMonitorRule,
  deleteWatchMonitorRule,
  getWatchMonitorRules,
  updateWatchMonitorRule,
} from "@/lib/api";
import type { MonitorRuleCreate, MonitorRuleUpdate } from "@/types/watchlist";

export function useMonitorRules(itemId?: string) {
  const queryClient = useQueryClient();

  const rulesQuery = useQuery({
    queryKey: ["watch-monitor", "rules", itemId ?? "all"],
    queryFn: () => getWatchMonitorRules(itemId),
  });

  const invalidateRules = () => {
    queryClient.invalidateQueries({ queryKey: ["watch-monitor", "rules"] });
    queryClient.invalidateQueries({ queryKey: ["watch-monitor"] });
  };

  const createMutation = useMutation({
    mutationFn: (data: MonitorRuleCreate) => createWatchMonitorRule(data),
    onSuccess: invalidateRules,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: MonitorRuleUpdate }) =>
      updateWatchMonitorRule(id, data),
    onSuccess: invalidateRules,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteWatchMonitorRule(id),
    onSuccess: invalidateRules,
  });

  return {
    rules: rulesQuery.data ?? [],
    isLoading: rulesQuery.isLoading,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    createRuleAsync: createMutation.mutateAsync,
    updateRuleAsync: updateMutation.mutateAsync,
    deleteRuleAsync: deleteMutation.mutateAsync,
  };
}
