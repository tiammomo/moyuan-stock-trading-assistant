"use client";

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useChatStore } from "@/stores/chatStore";
import { useChatStream } from "@/hooks/useChatStream";
import type { ChatFollowUpRequest, ChatRequest } from "@/types/chat";

const FOLLOW_UP_KEYWORDS = ["刚才", "上面", "这几只", "那几只", "比较", "对比", "排序", "打分"];

interface SubmitMessageOptions {
  preferFollowUp?: boolean;
  clearInput?: boolean;
}

function isStreaming(status: string): boolean {
  return status === "analyzing" || status === "running_skills" || status === "partial_ready";
}

export function useChatSubmit() {
  const queryClient = useQueryClient();
  const {
    currentSessionId,
    modeHint,
    messages,
    currentResult,
    setInputValue,
    streamingStatus,
  } = useChatStore();

  const { sendChat, sendFollowUp } = useChatStream({
    onComplete: (response) => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      queryClient.invalidateQueries({ queryKey: ["session", response.session_id] });
    },
  });

  const latestAssistantMessage = [...messages].reverse().find((message) => message.role === "assistant");
  const isSubmitting = isStreaming(streamingStatus);

  const submitMessage = useCallback(
    async (message: string, options: SubmitMessageOptions = {}) => {
      const normalizedMessage = message.trim();
      if (!normalizedMessage || isSubmitting) {
        return false;
      }

      const isSuggestedFollowUp = currentResult?.follow_ups?.includes(normalizedMessage) ?? false;
      const shouldUseFollowUp =
        !!currentSessionId &&
        !!latestAssistantMessage &&
        (
          options.preferFollowUp ||
          isSuggestedFollowUp ||
          FOLLOW_UP_KEYWORDS.some((keyword) => normalizedMessage.includes(keyword))
        );

      if (options.clearInput !== false) {
        setInputValue("");
      }

      if (shouldUseFollowUp && latestAssistantMessage) {
        const request: ChatFollowUpRequest = {
          session_id: currentSessionId!,
          parent_message_id: latestAssistantMessage.id,
          message: normalizedMessage,
          stream: true,
        };
        await sendFollowUp(request);
        return true;
      }

      const request: ChatRequest = {
        session_id: currentSessionId,
        message: normalizedMessage,
        mode_hint: modeHint,
        stream: true,
      };
      await sendChat(request);
      return true;
    },
    [
      currentResult?.follow_ups,
      currentSessionId,
      isSubmitting,
      latestAssistantMessage,
      modeHint,
      sendChat,
      sendFollowUp,
      setInputValue,
    ]
  );

  return {
    isSubmitting,
    submitMessage,
  };
}
