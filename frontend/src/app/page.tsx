"use client";

import { useEffect } from "react";
import { SessionList } from "@/components/workbench/SessionList";
import { MessageFlow } from "@/components/workbench/MessageFlow";
import { ChatComposer } from "@/components/workbench/ChatComposer";
import { ResultPanel } from "@/components/workbench/ResultPanel";
import { useUIStore } from "@/stores/uiStore";
import { useChatStore } from "@/stores/chatStore";
import { useSession } from "@/hooks/useSessions";
import { cn } from "@/lib/utils";

export default function WorkbenchPage() {
  const { leftPanelCollapsed, rightPanelCollapsed } = useUIStore();
  const { currentSessionId, setMessages } = useChatStore();
  const sessionQuery = useSession(currentSessionId);

  useEffect(() => {
    if (sessionQuery.data?.messages) {
      setMessages(sessionQuery.data.messages);
    }
  }, [sessionQuery.data, setMessages]);

  return (
    <div className="flex h-full">
      {/* Left Panel - Session List */}
      <div
        className={cn(
          "w-60 border-r bg-card flex flex-col transition-all",
          leftPanelCollapsed && "w-0 overflow-hidden border-0"
        )}
      >
        <SessionList />
      </div>

      {/* Center Panel - Message Flow + Input */}
      <div className="flex-1 flex flex-col min-w-0">
        <MessageFlow />
        <ChatComposer />
      </div>

      {/* Right Panel - Results */}
      <div
        className={cn(
          "w-[480px] flex flex-col transition-all",
          rightPanelCollapsed && "w-0 overflow-hidden border-0"
        )}
      >
        <ResultPanel />
      </div>
    </div>
  );
}
