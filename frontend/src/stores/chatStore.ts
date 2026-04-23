import { create } from "zustand";
import type { ChatMessageRecord, ChatResponse, ChatMode, StructuredResult } from "@/types";
import type { ChatResponseStatus } from "@/types/common";

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
  updateLatestAssistantMessage: (result: ChatResponse) => void;
  clearMessages: () => void;
  reset: () => void;
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

  updateLatestAssistantMessage: (result) =>
    set((state) => {
      const messages = [...state.messages];
      const assistantIndex = [...messages]
        .reverse()
        .findIndex((message) => message.role === "assistant");
      const resolvedAssistantIndex =
        assistantIndex === -1 ? -1 : messages.length - 1 - assistantIndex;

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
