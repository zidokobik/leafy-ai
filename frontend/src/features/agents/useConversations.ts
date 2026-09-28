import { useCallback, useEffect, useState } from "react";
import { chatApi } from "../../api/chat";
import type { ChatConversationSummary } from "../../api/contracts";

export type ConversationsStatus = "loading" | "ready" | "error";

type Snapshot = {
  conversations: ChatConversationSummary[];
  error: boolean;
};

/** Loads the stored conversation list and keeps it in sync with deletes and refreshes. */
export function useConversations() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    const load = async () => {
      try {
        const conversations = await chatApi.listConversations(
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setSnapshot({ conversations, error: false });
      } catch {
        if (controller.signal.aborted) return;
        // Keep the current list when a background refresh fails.
        setSnapshot(
          (previous) => previous ?? { conversations: [], error: true },
        );
      }
    };

    void load();
    return () => controller.abort();
  }, [version]);

  /** Refetch after an error, replacing the list with a loading state. */
  const retry = useCallback(() => {
    setSnapshot(null);
    setVersion((current) => current + 1);
  }, []);

  /** Background refetch that keeps the current list visible while updating. */
  const refresh = useCallback(() => {
    setVersion((current) => current + 1);
  }, []);

  const remove = useCallback(async (conversationId: string) => {
    await chatApi.removeConversation(conversationId);
    setSnapshot(
      (previous) =>
        previous && {
          ...previous,
          conversations: previous.conversations.filter(
            (conversation) => conversation.id !== conversationId,
          ),
        },
    );
  }, []);

  const status: ConversationsStatus =
    snapshot === null ? "loading" : snapshot.error ? "error" : "ready";

  return {
    conversations: snapshot?.conversations ?? [],
    status,
    retry,
    refresh,
    remove,
  };
}
