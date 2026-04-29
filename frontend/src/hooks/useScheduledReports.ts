"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getScheduledReportJobs,
  getScheduledReportRuns,
  triggerScheduledReport,
  updateScheduledReportJob,
} from "@/lib/api";
import type { ScheduledReportJobUpdate, ScheduledReportType } from "@/types/scheduledReport";

interface UseScheduledReportsOptions {
  runsLimit?: number;
  runsRefetchInterval?: number;
}

export function useScheduledReports(options?: UseScheduledReportsOptions) {
  const queryClient = useQueryClient();
  const runsLimit = options?.runsLimit ?? 12;
  const runsRefetchInterval = options?.runsRefetchInterval ?? 30000;

  const jobsQuery = useQuery({
    queryKey: ["scheduled-reports", "jobs"],
    queryFn: getScheduledReportJobs,
  });

  const runsQuery = useQuery({
    queryKey: ["scheduled-reports", "runs", runsLimit],
    queryFn: () => getScheduledReportRuns(runsLimit),
    refetchInterval: runsRefetchInterval,
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["scheduled-reports"] });
    queryClient.invalidateQueries({ queryKey: ["monitor-notifications"] });
  };

  const updateJobMutation = useMutation({
    mutationFn: ({ reportType, data }: { reportType: ScheduledReportType; data: ScheduledReportJobUpdate }) =>
      updateScheduledReportJob(reportType, data),
    onSuccess: invalidateAll,
  });

  const triggerJobMutation = useMutation({
    mutationFn: (reportType: ScheduledReportType) => triggerScheduledReport(reportType),
    onSuccess: invalidateAll,
  });

  return {
    jobs: jobsQuery.data ?? [],
    runs: runsQuery.data ?? [],
    isLoading: jobsQuery.isLoading || runsQuery.isLoading,
    isSaving: updateJobMutation.isPending,
    isTriggering: triggerJobMutation.isPending,
    updateJobAsync: updateJobMutation.mutateAsync,
    triggerJobAsync: triggerJobMutation.mutateAsync,
  };
}
