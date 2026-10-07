import { useEffect, useState } from "react";
import { TriangleAlertIcon } from "lucide-react";
import { chatApi } from "../../api/chat";
import type { ChatConversationDetail } from "../../api/contracts";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatSession } from "./ChatSession";

type SavedConversationProps = {
  conversationId: string;
  onResponseFinished: () => void;
};

/** Loads a stored conversation, then hands it to a chat session. */
export function SavedConversation({
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
