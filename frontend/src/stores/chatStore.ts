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
    facts: patch.facts ?? current?.facts ?? [],
    judgements: patch.judgements ?? current?.judgements ?? [],
    follow_ups: patch.follow_ups ?? current?.follow_ups ?? [],
    sources: patch.sources ?? current?.sources ?? [],
  };
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
    const latestAssistant = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");
    set({
      messages,
      currentResult: latestAssistant?.result_snapshot ?? null,
      partialSummary: "",
      streamingStatus: "idle",
    });
  },

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

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

      return {
        messages,
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
      return {
        messages,
        currentResult: {
          summary: result.summary,
          table: result.table,
          cards: result.cards,
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
