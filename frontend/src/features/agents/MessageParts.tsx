import { getToolName, isToolUIPart } from "ai";
import type { DynamicToolUIPart, ToolUIPart, UIMessage } from "ai";
import {
  BrainIcon,
  CheckIcon,
  ChevronRightIcon,
  LoaderCircleIcon,
  TriangleAlertIcon,
} from "lucide-react";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import { Markdown } from "@/components/ui/markdown";
import { Marker, MarkerContent, MarkerIcon } from "@/components/ui/marker";

type MessagePart = UIMessage["parts"][number];

const toolLabels: Record<string, string> = {
  get_sensor_history: "Reading sensor history",
  get_unix_timestamp: "Checking the current time",
};

function isVisiblePart(part: MessagePart): boolean {
  if (part.type === "text") return part.text.length > 0;
  if (part.type === "reasoning") {
    return part.text.length > 0 || part.state === "streaming";
  }
  return isToolUIPart(part);
}

function summarizeInput(input: unknown): string | null {
  if (input == null) return null;
  try {
    const text = JSON.stringify(input);
    if (!text || text === "{}") return null;
    return text.length > 100 ? `${text.slice(0, 100)}…` : text;
  } catch {
    return null;
  }
}

function ToolCallMarker({ part }: { part: ToolUIPart | DynamicToolUIPart }) {
  const name = getToolName(part);
  const label = toolLabels[name] ?? `Running ${name.replaceAll("_", " ")}`;
  const input = summarizeInput(part.input);
  const done = part.state === "output-available";
  const failed = part.state === "output-error" || part.state === "output-denied";
  const running = !done && !failed;

  return (
    <Marker>
      <MarkerIcon>
        {running ? (
          <LoaderCircleIcon className="animate-spin" />
        ) : done ? (
          <CheckIcon />
        ) : (
          <TriangleAlertIcon className="text-destructive" />
        )}
      </MarkerIcon>
      <MarkerContent>
        <span className={running ? "shimmer" : undefined}>{label}</span>
        {input && (
          <span className="ml-2 font-mono text-xs opacity-70">{input}</span>
        )}
        {part.state === "output-error" && (
          <span className="ml-2 text-destructive">{part.errorText}</span>
        )}
        {part.state === "output-denied" && (
          <span className="ml-2">Denied.</span>
        )}
      </MarkerContent>
    </Marker>
  );
}

function ReasoningBlock({
  part,
}: {
  part: Extract<MessagePart, { type: "reasoning" }>;
}) {
  const streaming = part.state === "streaming";
  if (!part.text && !streaming) return null;

  return (
    <details className="group/reasoning text-sm text-muted-foreground">
      <summary className="flex w-fit cursor-pointer list-none items-center gap-2 [&::-webkit-details-marker]:hidden">
        <BrainIcon className="size-4 shrink-0" />
        <span className={streaming ? "shimmer" : undefined}>
          {streaming ? "Reasoning…" : "Reasoning"}
        </span>
        <ChevronRightIcon className="size-3.5 shrink-0 transition-transform group-open/reasoning:rotate-90" />
      </summary>
      <div className="mt-1.5 ml-2 border-l-2 border-border pl-4 text-xs leading-relaxed whitespace-pre-wrap">
        {part.text}
      </div>
    </details>
  );
}

/** Renders an assistant message's parts in order: steps, tool calls, reasoning and text. */
export function AssistantParts({ message }: { message: UIMessage }) {
  const firstVisibleIndex = message.parts.findIndex(isVisiblePart);

  return (
    <>
      {message.parts.map((part, index) => {
        const key = `${message.id}-${index}`;

        if (part.type === "step-start") {
          // Only separate steps that follow visible content.
          return firstVisibleIndex !== -1 && index > firstVisibleIndex ? (
            <Marker key={key} variant="separator" aria-hidden="true" />
          ) : null;
        }

        if (part.type === "text") {
          if (!part.text) return null;
          return (
            <Bubble key={key} variant="muted">
              <BubbleContent>
                <Markdown>{part.text}</Markdown>
              </BubbleContent>
            </Bubble>
          );
        }

        if (part.type === "reasoning") {
          if (!isVisiblePart(part)) return null;
          return <ReasoningBlock key={key} part={part} />;
        }

        if (isToolUIPart(part)) {
          return <ToolCallMarker key={key} part={part} />;
        }

        return null;
      })}
    </>
  );
}
