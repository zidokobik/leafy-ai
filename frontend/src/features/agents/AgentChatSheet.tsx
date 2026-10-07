import { useRef, useState } from "react";
import { BotMessageSquareIcon, PlusIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { randomUUID } from "@/lib/utils";
import { ChatSession } from "./ChatSession";
import { SavedConversation } from "./SavedConversation";

/** Floating button that opens the agent chat in a right-side sheet. */
export function AgentChatSheet() {
  const [open, setOpen] = useState(false);
  const [conversationId, setConversationId] = useState<string>(() =>
    randomUUID(),
  );
  // Whether the backend persisted the conversation (a response finished).
  const savedRef = useRef(false);
  // Decided when the sheet opens so the branch stays stable while it is shown.
  const [resume, setResume] = useState(false);

  const handleOpenChange = (next: boolean) => {
    if (next) setResume(savedRef.current);
    setOpen(next);
  };

  const startNewChat = () => {
    setConversationId(randomUUID());
    savedRef.current = false;
    setResume(false);
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetTrigger asChild>
        <Button className="fixed right-6 bottom-6 z-40 rounded-full shadow-lg">
          <BotMessageSquareIcon /> Ask agent
        </Button>
      </SheetTrigger>
      <SheetContent
        side="right"
        className="gap-0 data-[side=right]:w-full data-[side=right]:sm:max-w-lg"
      >
        <SheetHeader className="flex-row items-center justify-between gap-2 border-b border-border pr-12">
          <div className="flex min-w-0 flex-col gap-0.5">
            <SheetTitle>Farm agent</SheetTitle>
            <SheetDescription>
              Conversations are saved to the Agents page.
            </SheetDescription>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="shrink-0"
            onClick={startNewChat}
          >
            <PlusIcon /> New chat
          </Button>
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col p-4">
          {resume ? (
            <SavedConversation
              key={conversationId}
              conversationId={conversationId}
              onResponseFinished={() => {
                savedRef.current = true;
              }}
            />
          ) : (
            <ChatSession
              key={conversationId}
              conversationId={conversationId}
              onResponseFinished={() => {
                savedRef.current = true;
              }}
            />
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
