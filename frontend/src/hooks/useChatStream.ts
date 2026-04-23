import { useCallback, useRef, useState } from "react";
import type {
  ChatFollowUpRequest,
  ChatRequest,
  ChatResponse,
  JsonValue,
  SkillUsage,
  StructuredResult,
  UserVisibleError,
} from "@/types";
import type { ChatMode, ChatResponseStatus, StreamEvent } from "@/types/common";
import { toast } from "@/components/ui/Toast";
import { extractApiErrorMessage } from "@/lib/apiError";
import { useChatStore } from "@/stores/chatStore";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SKILL_RUN_STATUSES = new Set<SkillUsage["status"]>(["pending", "running", "success", "failed"]);

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

function asRecord(value: JsonValue | undefined): Record<string, JsonValue> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, JsonValue>;
}

function asChatMode(value: JsonValue | undefined): ChatMode | null {
  if (typeof value !== "string") return null;
  return value as ChatMode;
}

function normalizePlannedSkills(value: JsonValue | undefined): SkillUsage[] {
  if (!Array.isArray(value)) return [];

  const skills: SkillUsage[] = [];
  for (const item of value) {
    const skill = asRecord(item);
    const name = typeof skill?.name === "string" ? skill.name : null;
    if (!name) continue;
    const reason = skill && typeof skill.reason === "string" ? skill.reason : null;
    skills.push({
      name,
      status: "pending",
      latency_ms: null,
      reason,
    });
  }
  return skills;
}

function normalizeFinishedSkill(value: Record<string, JsonValue>): SkillUsage | null {
  const name = typeof value.name === "string" ? value.name : null;
  if (!name) return null;

  const status =
    typeof value.status === "string" && SKILL_RUN_STATUSES.has(value.status as SkillUsage["status"])
      ? (value.status as SkillUsage["status"])
      : "success";

  return {
    name,
    status,
    latency_ms: typeof value.latency_ms === "number" ? value.latency_ms : null,
    reason: typeof value.reason === "string" ? value.reason : null,
  };
}

function mergeSkillUsage(existing: SkillUsage | undefined, incoming: SkillUsage): SkillUsage {
  return {
    name: incoming.name,
    status: incoming.status,
    latency_ms: incoming.latency_ms ?? existing?.latency_ms ?? null,
    reason: incoming.reason ?? existing?.reason ?? null,
  };
}

function upsertSkillUsage(skills: SkillUsage[], incoming: SkillUsage): SkillUsage[] {
  const skillIndex = skills.findIndex((skill) => skill.name === incoming.name);
  if (skillIndex === -1) {
    return [...skills, incoming];
  }

  return skills.map((skill, index) =>
    index === skillIndex ? mergeSkillUsage(skill, incoming) : skill
  );
}

function latestAssistantSkills(): SkillUsage[] {
  const latestAssistant = [...useChatStore.getState().messages]
    .reverse()
    .find((message) => message.role === "assistant");
  return latestAssistant?.skills_used || [];
}

function normalizeUserVisibleError(value: JsonValue | undefined): UserVisibleError | null {
  const error = asRecord(value);
  const code = typeof error?.code === "string" ? error.code : null;
  const title = typeof error?.title === "string" ? error.title : null;
  const message = typeof error?.message === "string" ? error.message : null;
  if (!code || !title || !message) return null;

  return {
    code,
    severity: error?.severity === "warning" ? "warning" : "error",
    title,
    message,
    retryable: Boolean(error?.retryable),
  };
}

function ensureUserVisibleError(
  error: UserVisibleError | null,
  fallbackMessage: string
): UserVisibleError {
  if (error) return error;
  return {
    code: "chat_request_failed",
    severity: "error",
    title: "请求失败",
    message: fallbackMessage,
    retryable: true,
  };
}

function showChatToast(error: UserVisibleError) {
  const message = `${error.title}：${error.message}`;
  if (error.severity === "warning") {
    toast.warning(message);
    return;
  }
  toast.error(message);
}

function buildResultSnapshot(
  summary: string,
  accumulatedResult: Partial<ChatResponse>
): StructuredResult {
  return {
    summary,
    table: accumulatedResult.table || null,
    cards: accumulatedResult.cards || [],
    facts: accumulatedResult.facts || [],
    judgements: accumulatedResult.judgements || [],
    follow_ups: accumulatedResult.follow_ups || [],
    sources: accumulatedResult.sources || [],
  };
}

function buildFailedResponse(
  data: Record<string, JsonValue> | null,
  {
    assistantPlaceholderId,
    userMessage,
    accumulatedResult,
    currentSkills,
  }: {
    assistantPlaceholderId: string;
    userMessage: StreamExecutionRequest["userMessage"];
    accumulatedResult: Partial<ChatResponse>;
    currentSkills: SkillUsage[];
  }
): ChatResponse {
  const rawError =
    (data && typeof data.error === "string" ? data.error : null) ||
    (typeof accumulatedResult.summary === "string" && accumulatedResult.summary) ||
    "请求失败";
  const userVisibleError = ensureUserVisibleError(
    normalizeUserVisibleError(data?.user_visible_error),
    rawError
  );
  const summary =
    (typeof accumulatedResult.summary === "string" && accumulatedResult.summary) || userVisibleError.message;

  return {
    session_id: (data && typeof data.session_id === "string" ? data.session_id : null) || userMessage.session_id || "",
    message_id: (data && typeof data.message_id === "string" ? data.message_id : null) || assistantPlaceholderId,
    mode:
      (data ? asChatMode(data.mode) : null) ||
      userMessage.mode ||
      "generic_data_query",
    skills_used:
      (data && Array.isArray(data.skills_used) ? (data.skills_used as unknown as SkillUsage[]) : null) ||
      currentSkills,
    summary,
    table: accumulatedResult.table || null,
    cards: accumulatedResult.cards || [],
    facts: accumulatedResult.facts || [],
    judgements: accumulatedResult.judgements || [],
    follow_ups: accumulatedResult.follow_ups || [],
    sources: accumulatedResult.sources || [],
    status: "failed",
    user_visible_error: userVisibleError,
  };
}

function buildCompletedResponse(
  data: Record<string, JsonValue>,
  {
    assistantPlaceholderId,
    userMessage,
    accumulatedResult,
    currentSkills,
  }: {
    assistantPlaceholderId: string;
    userMessage: StreamExecutionRequest["userMessage"];
    accumulatedResult: Partial<ChatResponse>;
    currentSkills: SkillUsage[];
  }
): ChatResponse {
  return {
    session_id:
      (typeof data.session_id === "string" ? data.session_id : null) || userMessage.session_id || "",
    message_id:
      (typeof data.message_id === "string" ? data.message_id : null) || assistantPlaceholderId,
    mode: asChatMode(data.mode) || userMessage.mode || "generic_data_query",
    skills_used:
      (Array.isArray(data.skills_used) ? (data.skills_used as unknown as SkillUsage[]) : null) ||
      currentSkills,
    summary:
      (typeof data.summary === "string" ? data.summary : null) ||
      (typeof accumulatedResult.summary === "string" ? accumulatedResult.summary : null) ||
      "",
    table:
      ((data.table as ChatResponse["table"] | undefined) ?? undefined) ||
      accumulatedResult.table ||
      null,
    cards:
      (Array.isArray(data.cards) ? (data.cards as unknown as ChatResponse["cards"]) : null) ||
      accumulatedResult.cards ||
      [],
    facts:
      (Array.isArray(data.facts) ? (data.facts as unknown as ChatResponse["facts"]) : null) ||
      accumulatedResult.facts ||
      [],
    judgements:
      (Array.isArray(data.judgements) ? (data.judgements as unknown as ChatResponse["judgements"]) : null) ||
      accumulatedResult.judgements ||
      [],
    follow_ups:
      (Array.isArray(data.follow_ups) ? (data.follow_ups as unknown as ChatResponse["follow_ups"]) : null) ||
      accumulatedResult.follow_ups ||
      [],
    sources:
      (Array.isArray(data.sources) ? (data.sources as unknown as ChatResponse["sources"]) : null) ||
      accumulatedResult.sources ||
      [],
    status:
      (typeof data.status === "string" ? (data.status as ChatResponseStatus) : null) || "completed",
    user_visible_error: normalizeUserVisibleError(data.user_visible_error),
  };
}

async function extractHttpError(response: Response): Promise<Error> {
  let message = `HTTP ${response.status}`;

  try {
    const payload = (await response.clone().json()) as Record<string, JsonValue>;
    message = extractApiErrorMessage(payload) || message;
  } catch {
    try {
      const text = (await response.text()).trim();
      if (text) {
        message = text.slice(0, 200);
      }
    } catch {
      // Ignore secondary parsing errors.
    }
  }

  return new Error(message);
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
    setCurrentResult,
    setCurrentSession,
    patchLatestAssistantMessage,
    updateLatestAssistantMessage,
  } = useChatStore();

  const executeStream = useCallback(
    async ({ endpoint, body, userMessage }: StreamExecutionRequest) => {
      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();
      let assistantPlaceholderCreated = false;
      const userMessageId = `msg_${Date.now()}`;
      const assistantPlaceholderId = `msg_${Date.now()}_assistant`;

      setStreamingState("connecting");
      setStreamingStatus("analyzing");
      setPartialSummary("");

      addMessage({
        id: userMessageId,
        session_id: userMessage.session_id || "",
        role: "user",
        content: userMessage.content,
        mode: userMessage.mode || null,
        skills_used: [],
        status: "idle",
        created_at: new Date().toISOString(),
      });

      try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...body, stream: true }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw await extractHttpError(response);
        }

        setStreamingState("streaming");

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

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
        assistantPlaceholderCreated = true;

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
                  setAutoDetectedMode(asChatMode(data.mode));
                  patchLatestAssistantMessage({
                    mode: asChatMode(data.mode),
                    status: "analyzing",
                  });
                  setStreamingStatus("running_skills");
                  break;

                case "skill_routing_ready":
                  patchLatestAssistantMessage({
                    skills_used: normalizePlannedSkills(data.skills),
                    status: "running_skills",
                  });
                  setStreamingStatus("running_skills");
                  break;

                case "skill_started":
                  if (typeof data.name === "string") {
                    patchLatestAssistantMessage({
                      skills_used: upsertSkillUsage(latestAssistantSkills(), {
                        name: data.name,
                        status: "running",
                        latency_ms: null,
                        reason: null,
                      }),
                      status: "running_skills",
                    });
                  }
                  setStreamingStatus("running_skills");
                  break;

                case "skill_finished": {
                  const finishedSkill = normalizeFinishedSkill(data);
                  if (finishedSkill) {
                    patchLatestAssistantMessage({
                      skills_used: upsertSkillUsage(latestAssistantSkills(), finishedSkill),
                      status: "running_skills",
                    });
                  }
                  break;
                }

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
                  patchLatestAssistantMessage({
                    content: typeof data.summary === "string" ? data.summary : undefined,
                    status: "partial_ready",
                    result_snapshot: {
                      summary:
                        typeof accumulatedResult.summary === "string" ? accumulatedResult.summary : "",
                      table: accumulatedResult.table || null,
                      cards: accumulatedResult.cards || [],
                      facts: accumulatedResult.facts || [],
                      judgements: accumulatedResult.judgements || [],
                      follow_ups: accumulatedResult.follow_ups || [],
                      sources: accumulatedResult.sources || [],
                    } satisfies Partial<StructuredResult>,
                  });
                  setStreamingStatus("partial_ready");
                  break;

                case "completed": {
                  const finalResponse = buildCompletedResponse(data, {
                    assistantPlaceholderId,
                    userMessage,
                    accumulatedResult,
                    currentSkills: latestAssistantSkills(),
                  });
                  setCurrentSession(finalResponse.session_id);
                  updateLatestAssistantMessage(finalResponse);
                  setStreamingStatus(finalResponse.status);
                  setStreamingState("done");
                  if (finalResponse.user_visible_error) {
                    showChatToast(finalResponse.user_visible_error);
                  }
                  options.onComplete?.(finalResponse);
                  break;
                }

                case "result_enhanced": {
                  const enhancedResponse = buildCompletedResponse(data, {
                    assistantPlaceholderId,
                    userMessage,
                    accumulatedResult,
                    currentSkills: latestAssistantSkills(),
                  });
                  setCurrentSession(enhancedResponse.session_id);
                  updateLatestAssistantMessage(enhancedResponse);
                  setStreamingStatus(enhancedResponse.status);
                  break;
                }

                case "failed": {
                  const failedResponse = buildFailedResponse(asRecord(data), {
                    assistantPlaceholderId,
                    userMessage,
                    accumulatedResult,
                    currentSkills: latestAssistantSkills(),
                  });
                  const failedError = ensureUserVisibleError(
                    failedResponse.user_visible_error,
                    failedResponse.summary
                  );
                  setCurrentSession(failedResponse.session_id || null);
                  updateLatestAssistantMessage(failedResponse);
                  setStreamingStatus("failed");
                  setStreamingState("error");
                  showChatToast(failedError);
                  options.onError?.(new Error(failedError.message));
                  break;
                }
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

        const failedResponse = buildFailedResponse(null, {
          assistantPlaceholderId,
          userMessage,
          accumulatedResult: {},
          currentSkills: latestAssistantSkills(),
        });
        const failedError = ensureUserVisibleError(
          failedResponse.user_visible_error,
          (err as Error).message || "请求失败"
        );
        failedError.message = (err as Error).message || "请求失败";
        failedResponse.user_visible_error = failedError;
        failedResponse.summary = failedError.message;

        setStreamingState("error");
        setStreamingStatus("failed");
        if (assistantPlaceholderCreated) {
          updateLatestAssistantMessage(failedResponse);
        } else {
          addMessage({
            id: assistantPlaceholderId,
            session_id: userMessage.session_id || "",
            role: "assistant",
            content: failedResponse.summary,
            mode: failedResponse.mode,
            skills_used: failedResponse.skills_used,
            result_snapshot: buildResultSnapshot(failedResponse.summary, {}),
            status: "failed",
            user_visible_error: failedError,
            created_at: new Date().toISOString(),
          });
          setCurrentResult(buildResultSnapshot(failedResponse.summary, {}));
        }
        showChatToast(failedError);
        options.onError?.(err as Error);
      }
    },
    [
      addMessage,
      options,
      patchLatestAssistantMessage,
      setAutoDetectedMode,
      setCurrentResult,
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
