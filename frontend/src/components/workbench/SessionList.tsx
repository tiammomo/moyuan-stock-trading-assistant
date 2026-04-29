"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { useSessions } from "@/hooks/useSessions";
import { useChatStore } from "@/stores/chatStore";
import { useUIStore } from "@/stores/uiStore";
import { cn, formatTimestamp, MODE_LABELS, MODE_COLORS } from "@/lib/utils";
import type { SessionSummary } from "@/types/session";

export function SessionList() {
  const { sessions, isLoading, createSession, closeSession, isCreating, isClosing } = useSessions();
  const { currentSessionId, setCurrentSession, clearMessages } = useChatStore();
  const { sessionSearchQuery, setSessionSearchQuery } = useUIStore();

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(sessionSearchQuery.toLowerCase())
  );

  const handleSelectSession = (session: SessionSummary) => {
    setCurrentSession(session.id);
    clearMessages();
  };

  const handleNewSession = () => {
    createSession();
    clearMessages();
  };

  const handleCloseSession = (event: React.MouseEvent<HTMLButtonElement>, sessionId: string) => {
    event.stopPropagation();
    closeSession(sessionId);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b bg-card/50 space-y-2">
        <Button
          onClick={handleNewSession}
          disabled={isCreating}
          className="w-full shadow-sm hover:shadow-md transition-shadow"
          size="sm"
        >
          <span className="mr-1">+</span> 新建会话
        </Button>
        <div className="relative">
          <Input
            placeholder="搜索会话..."
            value={sessionSearchQuery}
            onChange={(e) => setSessionSearchQuery(e.target.value)}
            className="h-8 text-xs pl-8"
          />
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/50 text-xs">
            🔍
          </span>
        </div>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-3 space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 bg-muted rounded-xl animate-pulse" />
            ))}
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="p-6 text-center">
            <div className="text-2xl mb-2">📭</div>
            <p className="text-xs text-muted-foreground">
              {sessionSearchQuery ? "没有匹配的会话" : "暂无会话记录"}
            </p>
            {!sessionSearchQuery && (
              <button
                onClick={handleNewSession}
                className="mt-3 text-xs text-primary hover:underline"
              >
                创建第一个会话
              </button>
            )}
          </div>
        ) : (
          <div className="p-2 space-y-1.5">
            {filteredSessions.map((session) => {
              const isActive = currentSessionId === session.id;
              return (
                <div
                  key={session.id}
                  className={cn(
                    "group relative rounded-xl transition-all duration-200",
                    isActive
                      ? "bg-gradient-to-r from-primary/10 to-primary/5 shadow-sm"
                      : "hover:bg-muted/70"
                  )}
                >
                  {/* Active indicator */}
                  {isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-r-full" />
                  )}

                  <div className="flex items-center">
                    <button
                      type="button"
                      onClick={() => handleSelectSession(session)}
                      className="min-w-0 flex-1 p-3 text-left"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium truncate text-foreground/90">
                          {session.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1.5">
                        {session.mode && (
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-[10px] px-1.5 py-0 font-medium",
                              MODE_COLORS[session.mode]
                            )}
                          >
                            {MODE_LABELS[session.mode]}
                          </Badge>
                        )}
                        <span className="text-[10px] text-muted-foreground">
                          {formatTimestamp(session.updated_at)}
                        </span>
                      </div>
                    </button>

                    {/* Close button */}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={isClosing}
                      onClick={(event) => handleCloseSession(event, session.id)}
                      className={cn(
                        "mr-2 h-7 w-7 p-0 rounded-lg opacity-0 group-hover:opacity-100 transition-all",
                        "hover:bg-red-50 hover:text-red-500",
                        isActive && "opacity-100"
                      )}
                      title="关闭会话"
                    >
                      ✕
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
