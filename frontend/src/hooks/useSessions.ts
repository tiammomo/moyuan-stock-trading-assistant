import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSessions, getSession, createSession, closeSession } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";

export function useSessions() {
  const queryClient = useQueryClient();

  const sessionsQuery = useQuery({
    queryKey: ["sessions"],
    queryFn: getSessions,
  });

  const createMutation = useMutation({
    mutationFn: createSession,
    onSuccess: (newSession) => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      useChatStore.getState().setCurrentSession(newSession.id);
    },
  });

  const closeMutation = useMutation({
    mutationFn: closeSession,
    onSuccess: (_result, closedSessionId) => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      queryClient.removeQueries({ queryKey: ["session", closedSessionId] });

      const chatStore = useChatStore.getState();
      if (chatStore.currentSessionId === closedSessionId) {
        chatStore.setCurrentSession(null);
        chatStore.clearMessages();
      }
    },
  });

  return {
    sessions: sessionsQuery.data ?? [],
    isLoading: sessionsQuery.isLoading,
    isError: sessionsQuery.isError,
    createSession: createMutation.mutate,
    closeSession: closeMutation.mutate,
    isCreating: createMutation.isPending,
    isClosing: closeMutation.isPending,
  };
}

export function useSession(id: string | null) {
  return useQuery({
    queryKey: ["session", id],
    queryFn: () => getSession(id!),
    enabled: !!id,
  });
}
