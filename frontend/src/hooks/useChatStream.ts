import { useCallback, useRef, useState } from "react";
import type { ChatFollowUpRequest, ChatRequest, ChatResponse } from "@/types";
import type { ChatMode, ChatResponseStatus, StreamEvent } from "@/types/common";
import { useChatStore } from "@/stores/chatStore";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type StreamingState = "idle" | "connecting" | "streaming" | "done" | "error";

interface UseChatStreamOptions {
  onEvent?: (event: StreamEvent) => void;
  onComplete?: (response: ChatResponse) => void;
  onError?: (error: Error) => void;
}

interface StreamExecutionRequest {
  endpoint: string;
  body: ChatRequest | ChatFollowUpRequest;
  userMessage: {
    session_id?: string | null;
    content: string;
    mode?: ChatMode | null;
  };
}

export function useChatStream(options: UseChatStreamOptions = {}) {
  const [streamingState, setStreamingState] = useState<StreamingState>("idle");
  const [latestEvent, setLatestEvent] = useState<StreamEvent | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const {
    setStreamingStatus,
    setAutoDetectedMode,
    setPartialSummary,
    addMessage,
    setCurrentSession,
    updateLatestAssistantMessage,
  } = useChatStore();

  const executeStream = useCallback(
    async ({ endpoint, body, userMessage }: StreamExecutionRequest) => {
      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();

      setStreamingState("connecting");
      setStreamingStatus("analyzing");

      try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...body, stream: true }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        setStreamingState("streaming");

        addMessage({
          id: `msg_${Date.now()}`,
          session_id: userMessage.session_id || "",
          role: "user",
          content: userMessage.content,
          mode: userMessage.mode || null,
          skills_used: [],
          status: "idle",
          created_at: new Date().toISOString(),
        });

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const assistantPlaceholderId = `msg_${Date.now()}_assistant`;
        addMessage({
          id: assistantPlaceholderId,
          session_id: userMessage.session_id || "",
          role: "assistant",
          content: "",
          mode: null,
          skills_used: [],
          status: "analyzing",
          created_at: new Date().toISOString(),
        });

        const decoder = new TextDecoder();
        let buffer = "";
        let accumulatedResult: Partial<ChatResponse> = {};

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data:")) continue;

            try {
              const data = JSON.parse(line.slice(5).trim());
              const event: StreamEvent = {
                event: data.event || data.type,
                data,
                emitted_at: data.emitted_at || null,
              };

              setLatestEvent(event);
              options.onEvent?.(event);

              switch (event.event) {
                case "mode_detected":
                  setAutoDetectedMode(data.mode);
                  setStreamingStatus("running_skills");
                  break;

                case "skill_started":
                  setStreamingStatus("running_skills");
                  break;

                case "partial_result":
                  if (data.summary) {
                    setPartialSummary(data.summary);
                    accumulatedResult.summary = data.summary;
                  }
                  if (data.table) accumulatedResult.table = data.table;
                  if (data.cards) accumulatedResult.cards = data.cards;
                  if (data.facts) accumulatedResult.facts = data.facts;
                  if (data.judgements) accumulatedResult.judgements = data.judgements;
                  if (data.follow_ups) accumulatedResult.follow_ups = data.follow_ups;
                  if (data.sources) accumulatedResult.sources = data.sources;
                  setStreamingStatus("partial_ready");
                  break;

                case "completed": {
                  const finalResponse: ChatResponse = {
                    session_id: data.session_id || userMessage.session_id || "",
                    message_id: data.message_id || assistantPlaceholderId,
                    mode: data.mode || userMessage.mode || "generic_data_query",
                    skills_used: data.skills_used || [],
                    summary: data.summary || accumulatedResult.summary || "",
                    table: data.table || accumulatedResult.table || null,
                    cards: data.cards || accumulatedResult.cards || [],
                    facts: data.facts || accumulatedResult.facts || [],
                    judgements: data.judgements || accumulatedResult.judgements || [],
                    follow_ups: data.follow_ups || accumulatedResult.follow_ups || [],
                    sources: data.sources || accumulatedResult.sources || [],
                    status: (data.status || "completed") as ChatResponseStatus,
                  };
                  setCurrentSession(finalResponse.session_id);
                  updateLatestAssistantMessage(finalResponse);
                  setStreamingStatus(finalResponse.status);
                  setStreamingState("done");
                  options.onComplete?.(finalResponse);
                  break;
                }

                case "failed":
                  setStreamingStatus("failed");
                  setStreamingState("error");
                  options.onError?.(new Error(data.error || "Request failed"));
                  break;
              }
            } catch {
              // Skip invalid JSON lines.
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setStreamingState("idle");
          return;
        }
        setStreamingState("error");
        setStreamingStatus("failed");
        options.onError?.(err as Error);
      }
    },
    [
      addMessage,
      options,
      setAutoDetectedMode,
      setCurrentSession,
      setPartialSummary,
      setStreamingStatus,
      updateLatestAssistantMessage,
    ]
  );

  const sendChat = useCallback(
    async (request: ChatRequest) =>
      executeStream({
        endpoint: "/api/chat",
        body: request,
        userMessage: {
          session_id: request.session_id,
          content: request.message,
          mode: request.mode_hint || null,
        },
      }),
    [executeStream]
  );

  const sendFollowUp = useCallback(
    async (request: ChatFollowUpRequest) =>
      executeStream({
        endpoint: "/api/chat/follow-up",
        body: request,
        userMessage: {
          session_id: request.session_id,
          content: request.message,
          mode: null,
        },
      }),
    [executeStream]
  );

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort();
    setStreamingState("idle");
    setStreamingStatus("idle");
  }, [setStreamingStatus]);

  return {
    streamingState,
    latestEvent,
    sendChat,
    sendFollowUp,
    cancel,
  };
}
