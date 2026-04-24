import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getWatchMonitorEvents,
  getWatchMonitorStatus,
  triggerWatchMonitorScan,
} from "@/lib/api";

export function useWatchMonitor() {
  const queryClient = useQueryClient();

  const statusQuery = useQuery({
    queryKey: ["watch-monitor", "status"],
    queryFn: getWatchMonitorStatus,
    refetchInterval: 30000,
  });

  const eventsQuery = useQuery({
    queryKey: ["watch-monitor", "events"],
    queryFn: () => getWatchMonitorEvents(8),
    refetchInterval: 30000,
  });

  const scanMutation = useMutation({
    mutationFn: triggerWatchMonitorScan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watch-monitor"] });
    },
  });

  return {
    status: statusQuery.data ?? null,
    events: eventsQuery.data ?? [],
    isLoading: statusQuery.isLoading || eventsQuery.isLoading,
    isScanning: scanMutation.isPending,
    triggerScanAsync: scanMutation.mutateAsync,
  };
}
