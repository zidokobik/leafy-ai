import { useEffect, useState } from "react";
import {
  CalendarClockIcon,
  MessageSquareIcon,
  PlusIcon,
  Trash2Icon,
  TriangleAlertIcon,
} from "lucide-react";
import { chatApi } from "../../api/chat";
import type {
  ChatConversationDetail,
  ChatConversationSummary,
} from "../../api/contracts";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { ChatSession } from "./ChatSession";
import { useConversations } from "./useConversations";

function formatWhen(iso: string): string {
  const date = new Date(iso);
  const sameDay = date.toDateString() === new Date().toDateString();
  return sameDay
    ? date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

type ConversationListProps = {
  conversations: ChatConversationSummary[];
  status: "loading" | "ready" | "error";
  activeId: string;
  onSelect: (conversationId: string) => void;
  onDelete: (conversationId: string) => void;
  onRetry: () => void;
};

function ConversationList({
  conversations,
  status,
  activeId,
  onSelect,
  onDelete,
  onRetry,
}: ConversationListProps) {
  if (status === "loading") {
    return (
      <div className="flex flex-col gap-2 p-2">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-11 w-full" />
        ))}
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex flex-col items-center gap-2 p-4 text-center text-sm text-muted-foreground">
        Could not load conversations.
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <p className="p-4 text-center text-sm text-muted-foreground">
        No conversations yet. Chats and scheduled agent runs will show up here.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-0.5 p-2">
      {conversations.map((conversation) => (
        <div key={conversation.id} className="group relative">
          <button
            type="button"
            onClick={() => onSelect(conversation.id)}
            className={cn(
              "flex w-full flex-col gap-0.5 rounded-md px-2.5 py-2 text-left text-sm hover:bg-muted",
              conversation.id === activeId && "bg-muted",
            )}
          >
            <span className="truncate pr-6">{conversation.title}</span>
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              {conversation.source === "schedule" ? (
                <CalendarClockIcon className="size-3 shrink-0" />
              ) : (
                <MessageSquareIcon className="size-3 shrink-0" />
              )}
              {formatWhen(conversation.updatedAt)}
            </span>
          </button>
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            aria-label={`Delete conversation "${conversation.title}"`}
            className="absolute top-1/2 right-1.5 -translate-y-1/2 opacity-0 group-focus-within:opacity-100 group-hover:opacity-100"
            onClick={() => onDelete(conversation.id)}
          >
            <Trash2Icon />
          </Button>
        </div>
      ))}
    </div>
  );
}

type SavedConversationProps = {
  conversationId: string;
  onResponseFinished: () => void;
};

/** Loads a stored conversation, then hands it to a chat session. */
function SavedConversation({
  conversationId,
  onResponseFinished,
}: SavedConversationProps) {
  const [detail, setDetail] = useState<ChatConversationDetail | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    chatApi
      .getConversation(conversationId, controller.signal)
      .then(setDetail)
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [conversationId]);

  if (failed) {
    return (
      <Card className="min-h-0 min-w-0 flex-1 items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <TriangleAlertIcon />
          <AlertTitle>Could not load the conversation</AlertTitle>
          <AlertDescription>
            It may have been deleted. Pick another conversation or start a new
            chat.
          </AlertDescription>
        </Alert>
      </Card>
    );
  }

  if (!detail) {
    return (
      <Card className="min-h-0 min-w-0 flex-1 gap-3 p-4">
        <Skeleton className="h-9 w-2/5 self-end" />
        <Skeleton className="h-20 w-3/5" />
        <Skeleton className="h-9 w-1/3 self-end" />
        <Skeleton className="h-14 w-1/2" />
      </Card>
    );
  }

  return (
    <ChatSession
      conversationId={conversationId}
      initialMessages={detail.messages}
      readOnly={detail.source === "schedule"}
      onResponseFinished={onResponseFinished}
    />
  );
}

export function AgentsPage() {
  const { conversations, status, retry, refresh, remove } = useConversations();
  const [activeId, setActiveId] = useState<string>(() => crypto.randomUUID());
  const [isNew, setIsNew] = useState(true);

  const startNewChat = () => {
    setActiveId(crypto.randomUUID());
    setIsNew(true);
  };

  const openConversation = (conversationId: string) => {
    if (conversationId === activeId) return;
    setActiveId(conversationId);
    setIsNew(false);
  };

  const deleteConversation = async (conversationId: string) => {
    try {
      await remove(conversationId);
    } catch {
      refresh();
      return;
    }
    if (conversationId === activeId) startNewChat();
  };

  return (
    <section className="flex h-[calc(100svh-10rem)] min-h-105 flex-col gap-4">
      <header>
        <h1 className="text-2xl font-medium tracking-tight">Agent</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask the Leafy agent about your farm. Conversations are saved, along
          with every scheduled agent run.
        </p>
      </header>

      <div className="flex min-h-0 flex-1 gap-4">
        <Card className="hidden w-64 shrink-0 flex-col gap-0 overflow-hidden p-0 md:flex">
          <div className="flex shrink-0 items-center justify-between border-b border-border p-3">
            <span className="text-sm font-medium">History</span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={startNewChat}
            >
              <PlusIcon /> New chat
            </Button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <ConversationList
              conversations={conversations}
              status={status}
              activeId={activeId}
              onSelect={openConversation}
              onDelete={(conversationId) =>
                void deleteConversation(conversationId)
              }
              onRetry={retry}
            />
          </div>
        </Card>

        {isNew ? (
          <ChatSession
            key={activeId}
            conversationId={activeId}
            onResponseFinished={refresh}
          />
        ) : (
          <SavedConversation
            key={activeId}
            conversationId={activeId}
            onResponseFinished={refresh}
          />
        )}
      </div>
    </section>
  );
}
