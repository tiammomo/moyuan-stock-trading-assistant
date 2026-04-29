import { create } from "zustand";
import type {
  ChatMessageRecord,
  ChatResponse,
  ChatMode,
  StructuredResult,
  SkillUsage,
} from "@/types";
import type { ChatResponseStatus } from "@/types/common";

type LatestAssistantMessagePatch = Omit<Partial<ChatMessageRecord>, "result_snapshot" | "skills_used"> & {
  skills_used?: SkillUsage[];
  result_snapshot?: Partial<StructuredResult> | null;
};

interface ChatState {
  currentSessionId: string | null;
  messages: ChatMessageRecord[];
  inputValue: string;
  modeHint: ChatMode | null;
  autoDetectedMode: ChatMode | null;
  streamingStatus: ChatResponseStatus;
  currentResult: StructuredResult | null;
  partialSummary: string;

  setCurrentSession: (id: string | null) => void;
  setInputValue: (value: string) => void;
  setModeHint: (mode: ChatMode | null) => void;
  setAutoDetectedMode: (mode: ChatMode | null) => void;
  setStreamingStatus: (status: ChatResponseStatus) => void;
  setCurrentResult: (result: StructuredResult | null) => void;
  setPartialSummary: (summary: string) => void;
  setMessages: (messages: ChatMessageRecord[]) => void;
  addMessage: (message: ChatMessageRecord) => void;
  prepareRetryAttempt: (messageContent: string) => void;
  patchLatestAssistantMessage: (patch: LatestAssistantMessagePatch) => void;
  updateLatestAssistantMessage: (result: ChatResponse) => void;
  clearMessages: () => void;
  reset: () => void;
}

function findLatestAssistantIndex(messages: ChatMessageRecord[]): number {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === "assistant") {
      return index;
    }
  }
  return -1;
}

function mergeStructuredResult(
  current: StructuredResult | null | undefined,
  patch: Partial<StructuredResult> | null | undefined
): StructuredResult | null | undefined {
  if (patch === undefined) return current;
  if (patch === null) return null;

  return {
    summary: patch.summary ?? current?.summary ?? "",
    table: patch.table ?? current?.table ?? null,
    cards: patch.cards ?? current?.cards ?? [],
    chart_config: patch.chart_config ?? current?.chart_config ?? null,
    facts: patch.facts ?? current?.facts ?? [],
    judgements: patch.judgements ?? current?.judgements ?? [],
    follow_ups: patch.follow_ups ?? current?.follow_ups ?? [],
    sources: patch.sources ?? current?.sources ?? [],
  };
}

function normalizeRetryMessageContent(value: string): string {
  return String(value || "").split(/\s+/).filter(Boolean).join(" ").trim();
}

function collapseRetryExchanges(messages: ChatMessageRecord[]): ChatMessageRecord[] {
  const collapsed: ChatMessageRecord[] = [];

  for (let index = 0; index < messages.length; index += 1) {
    const current = messages[index];
    const next = messages[index + 1];

    if (current.role === "user" && next?.role === "assistant") {
      const prevUser = collapsed.at(-2);
      const prevAssistant = collapsed.at(-1);
      const sameContent =
        prevUser?.role === "user" &&
        normalizeRetryMessageContent(prevUser.content) === normalizeRetryMessageContent(current.content);
      const previousFailed = prevAssistant?.role === "assistant" && prevAssistant.status === "failed";

      if (sameContent && previousFailed) {
        collapsed.splice(-2, 2, current, next);
      } else {
        collapsed.push(current, next);
      }
      index += 1;
      continue;
    }

    collapsed.push(current);
  }

  return collapsed;
}

function mergeMessageRecords(
  current: ChatMessageRecord,
  incoming: ChatMessageRecord
): ChatMessageRecord {
  return {
    ...current,
    ...incoming,
    parent_message_id: incoming.parent_message_id ?? current.parent_message_id,
    skills_used: incoming.skills_used.length > 0 ? incoming.skills_used : current.skills_used,
    result_snapshot:
      incoming.result_snapshot !== undefined
        ? mergeStructuredResult(current.result_snapshot, incoming.result_snapshot) ?? null
        : current.result_snapshot,
    user_visible_error:
      incoming.user_visible_error !== undefined ? incoming.user_visible_error : current.user_visible_error,
  };
}

function dedupeMessages(messages: ChatMessageRecord[]): ChatMessageRecord[] {
  const deduped: ChatMessageRecord[] = [];
  const indexById = new Map<string, number>();

  for (const message of messages) {
    const existingIndex = indexById.get(message.id);
    if (existingIndex === undefined) {
      indexById.set(message.id, deduped.length);
      deduped.push(message);
      continue;
    }

    deduped[existingIndex] = mergeMessageRecords(deduped[existingIndex], message);
  }

  return collapseRetryExchanges(deduped);
}

function upsertMessage(messages: ChatMessageRecord[], message: ChatMessageRecord): ChatMessageRecord[] {
  const nextMessages = [...messages, message];
  return dedupeMessages(nextMessages);
}

const initialState = {
  currentSessionId: null,
  messages: [],
  inputValue: "",
  modeHint: null,
  autoDetectedMode: null,
  streamingStatus: "idle" as ChatResponseStatus,
  currentResult: null,
  partialSummary: "",
};

export const useChatStore = create<ChatState>((set) => ({
  ...initialState,

  setCurrentSession: (id) => set({ currentSessionId: id }),
  setInputValue: (value) => set({ inputValue: value }),
  setModeHint: (mode) => set({ modeHint: mode }),
  setAutoDetectedMode: (mode) => set({ autoDetectedMode: mode }),
  setStreamingStatus: (status) => set({ streamingStatus: status }),
  setCurrentResult: (result) => set({ currentResult: result }),
  setPartialSummary: (summary) => set({ partialSummary: summary }),
  setMessages: (messages) => {
    const dedupedMessages = dedupeMessages(messages);
    const latestAssistant = [...dedupedMessages]
      .reverse()
      .find((message) => message.role === "assistant");
    set({
      messages: dedupedMessages,
      currentResult: latestAssistant?.result_snapshot ?? null,
      partialSummary: "",
      streamingStatus: "idle",
    });
  },

  addMessage: (message) =>
    set((state) => ({ messages: upsertMessage(state.messages, message) })),

  prepareRetryAttempt: (messageContent) =>
    set((state) => {
      const normalizedIncoming = normalizeRetryMessageContent(messageContent);
      if (!normalizedIncoming) return state;

      const messages = [...state.messages];
      const lastAssistant = messages.at(-1);
      const lastUser = messages.at(-2);
      const canReplace =
        lastAssistant?.role === "assistant" &&
        lastAssistant.status === "failed" &&
        lastUser?.role === "user" &&
        normalizeRetryMessageContent(lastUser.content) === normalizedIncoming;

      if (!canReplace) return state;

      messages.splice(-2, 2);
      const latestAssistant = [...messages].reverse().find((message) => message.role === "assistant");

      return {
        messages,
        currentResult: latestAssistant?.result_snapshot ?? null,
        partialSummary: "",
      };
    }),

  patchLatestAssistantMessage: (patch) =>
    set((state) => {
      const messages = [...state.messages];
      const assistantIndex = findLatestAssistantIndex(messages);
      if (assistantIndex === -1) return state;

      const currentMessage = messages[assistantIndex];
      const { result_snapshot: resultSnapshotPatch, ...messagePatch } = patch;
      const nextResultSnapshot = mergeStructuredResult(currentMessage.result_snapshot, resultSnapshotPatch);

      messages[assistantIndex] = {
        ...currentMessage,
        ...messagePatch,
        result_snapshot: nextResultSnapshot,
      };
      const dedupedMessages = dedupeMessages(messages);

      return {
        messages: dedupedMessages,
        currentResult: resultSnapshotPatch !== undefined ? nextResultSnapshot ?? null : state.currentResult,
      };
    }),

  updateLatestAssistantMessage: (result) =>
    set((state) => {
      const messages = [...state.messages];
      const resolvedAssistantIndex = findLatestAssistantIndex(messages);

      if (resolvedAssistantIndex >= 0) {
        messages[resolvedAssistantIndex] = {
          ...messages[resolvedAssistantIndex],
          id: result.message_id,
          session_id: result.session_id,
          content: result.summary,
          mode: result.mode,
          result_snapshot: {
            summary: result.summary,
            table: result.table,
            cards: result.cards,
            chart_config: result.chart_config,
            facts: result.facts,
            judgements: result.judgements,
            follow_ups: result.follow_ups,
            sources: result.sources,
          },
          skills_used: result.skills_used,
          status: result.status,
          user_visible_error: result.user_visible_error,
        };

        for (let i = resolvedAssistantIndex - 1; i >= 0; i -= 1) {
          if (messages[i].role === "user") {
            messages[i] = { ...messages[i], session_id: result.session_id };
            break;
          }
        }
      }
      const dedupedMessages = dedupeMessages(messages);
      return {
        messages: dedupedMessages,
        currentResult: {
          summary: result.summary,
          table: result.table,
          cards: result.cards,
          chart_config: result.chart_config,
          facts: result.facts,
          judgements: result.judgements,
          follow_ups: result.follow_ups,
          sources: result.sources,
        },
        partialSummary: "",
      };
    }),

  clearMessages: () => set({ messages: [], currentResult: null, partialSummary: "" }),

  reset: () => set(initialState),
}));
