import { useState } from "react";
import type { FormEvent } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { BotIcon, SendHorizonalIcon } from "lucide-react";
import { apiConfig } from "../../api/config";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Markdown } from "@/components/ui/markdown";
import {
  Message,
  MessageAvatar,
  MessageContent,
} from "@/components/ui/message";
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller";

const suggestions = ["What is the water pH level?"];

const transport = new DefaultChatTransport({
  api: `${apiConfig.baseUrl}/api/v1/chat`,
  credentials: "include",
});

export function AgentsPage() {
  const [input, setInput] = useState("");
  const { messages, sendMessage, status, error } = useChat({ transport });
  const isBusy = status !== "ready" && status !== "error";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isBusy) return;
    void sendMessage({ text: trimmed });
    setInput("");
  };

  return (
    <section className="flex h-[calc(100svh-10rem)] min-h-105 flex-col gap-4">
      <header>
        <h1 className="text-2xl font-medium tracking-tight">Agent</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask the Leafy agent about your farm. It cannot read sensors or control
          equipment yet.
        </p>
      </header>

      <Card className="min-h-0 flex-1 gap-0 p-0">
        <MessageScrollerProvider autoScroll>
          <MessageScroller>
            <MessageScrollerViewport>
              <MessageScrollerContent className="p-4">
                {messages.length === 0 ? (
                  <div className="m-auto flex max-w-md flex-col items-center gap-3 py-12 text-center">
                    <Avatar size="lg">
                      <AvatarFallback>
                        <BotIcon className="size-5" />
                      </AvatarFallback>
                    </Avatar>
                    <h2 className="text-base font-medium">
                      Ask about your farm
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      Get a quick status update or ask a question about the
                      hydroponic system.
                    </p>
                    <div className="flex flex-wrap justify-center gap-2">
                      {suggestions.map((suggestion) => (
                        <Button
                          key={suggestion}
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setInput(suggestion)}
                        >
                          {suggestion}
                        </Button>
                      ))}
                    </div>
                  </div>
                ) : (
                  messages.map((message) => (
                    <MessageScrollerItem
                      key={message.id}
                      messageId={message.id}
                      scrollAnchor={message.role === "user"}
                    >
                      <Message
                        align={message.role === "user" ? "end" : "start"}
                      >
                        <MessageAvatar>
                          <Avatar size="sm">
                            <AvatarFallback>
                              {message.role === "user" ? (
                                "You"
                              ) : (
                                <BotIcon className="size-4" />
                              )}
                            </AvatarFallback>
                          </Avatar>
                        </MessageAvatar>
                        <MessageContent>
                          <Bubble
                            align={message.role === "user" ? "end" : "start"}
                            variant={
                              message.role === "user" ? "default" : "muted"
                            }
                          >
                            <BubbleContent>
                              {message.parts.map((part, index) =>
                                part.type === "text" ? (
                                  <Markdown key={`${message.id}-${index}`}>
                                    {part.text}
                                  </Markdown>
                                ) : null,
                              )}
                            </BubbleContent>
                          </Bubble>
                        </MessageContent>
                      </Message>
                    </MessageScrollerItem>
                  ))
                )}

                {status === "submitted" && (
                  <Message align="start">
                    <MessageAvatar>
                      <Avatar size="sm">
                        <AvatarFallback>
                          <BotIcon className="size-4" />
                        </AvatarFallback>
                      </Avatar>
                    </MessageAvatar>
                    <MessageContent>
                      <Bubble variant="muted">
                        <BubbleContent className="shimmer">
                          Thinking…
                        </BubbleContent>
                      </Bubble>
                    </MessageContent>
                  </Message>
                )}
              </MessageScrollerContent>
            </MessageScrollerViewport>
            <MessageScrollerButton />
          </MessageScroller>
        </MessageScrollerProvider>

        {error && (
          <Alert variant="destructive" className="mx-4 mb-2 shrink-0">
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
        )}

        <form
          onSubmit={submit}
          className="flex shrink-0 items-center gap-2 border-t border-border p-3"
        >
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about your farm..."
            autoComplete="off"
          />
          <Button
            type="submit"
            size="icon"
            disabled={!input.trim() || isBusy}
            aria-label="Send message"
          >
            <SendHorizonalIcon />
          </Button>
        </form>
      </Card>
    </section>
  );
}
