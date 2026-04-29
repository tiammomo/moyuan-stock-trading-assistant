"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createMonitorNotificationChannel,
  deleteMonitorNotificationChannel,
  getMonitorNotificationChannels,
  getMonitorNotificationDeliveries,
  getMonitorNotificationSettings,
  testMonitorNotificationChannel,
  updateMonitorNotificationChannel,
  updateMonitorNotificationSettings,
} from "@/lib/api";
import type {
  MonitorNotificationChannelCreate,
  MonitorNotificationChannelUpdate,
  MonitorNotificationSettingsUpdate,
} from "@/types/notification";

interface UseMonitorNotificationsOptions {
  includeSettings?: boolean;
  includeDeliveries?: boolean;
}

export function useMonitorNotifications(options: UseMonitorNotificationsOptions = {}) {
  const queryClient = useQueryClient();
  const includeSettings = options.includeSettings ?? true;
  const includeDeliveries = options.includeDeliveries ?? true;

  const channelsQuery = useQuery({
    queryKey: ["monitor-notifications", "channels"],
    queryFn: getMonitorNotificationChannels,
  });

  const settingsQuery = useQuery({
    queryKey: ["monitor-notifications", "settings"],
    queryFn: getMonitorNotificationSettings,
    enabled: includeSettings,
  });

  const deliveriesQuery = useQuery({
    queryKey: ["monitor-notifications", "deliveries"],
    queryFn: () => getMonitorNotificationDeliveries(12),
    refetchInterval: 30000,
    enabled: includeDeliveries,
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["monitor-notifications"] });
    queryClient.invalidateQueries({ queryKey: ["watch-monitor"] });
  };

  const createChannelMutation = useMutation({
    mutationFn: (data: MonitorNotificationChannelCreate) => createMonitorNotificationChannel(data),
    onSuccess: invalidateAll,
  });

  const updateChannelMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: MonitorNotificationChannelUpdate }) =>
      updateMonitorNotificationChannel(id, data),
    onSuccess: invalidateAll,
  });

  const deleteChannelMutation = useMutation({
    mutationFn: (id: string) => deleteMonitorNotificationChannel(id),
    onSuccess: invalidateAll,
  });

  const testChannelMutation = useMutation({
    mutationFn: (id: string) => testMonitorNotificationChannel(id),
    onSuccess: invalidateAll,
  });

  const updateSettingsMutation = useMutation({
    mutationFn: (data: MonitorNotificationSettingsUpdate) => updateMonitorNotificationSettings(data),
    onSuccess: invalidateAll,
  });

  return {
    channels: channelsQuery.data ?? [],
    settings: settingsQuery.data ?? null,
    deliveries: deliveriesQuery.data ?? [],
    isLoading:
      channelsQuery.isLoading ||
      (includeSettings && settingsQuery.isLoading) ||
      (includeDeliveries && deliveriesQuery.isLoading),
    isSavingChannel: createChannelMutation.isPending || updateChannelMutation.isPending,
    isDeletingChannel: deleteChannelMutation.isPending,
    isTestingChannel: testChannelMutation.isPending,
    isSavingSettings: updateSettingsMutation.isPending,
    createChannelAsync: createChannelMutation.mutateAsync,
    updateChannelAsync: updateChannelMutation.mutateAsync,
    deleteChannelAsync: deleteChannelMutation.mutateAsync,
    testChannelAsync: testChannelMutation.mutateAsync,
    updateSettingsAsync: updateSettingsMutation.mutateAsync,
  };
}
