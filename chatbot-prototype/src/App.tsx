import { useState } from "react";
import { useChat } from "@ai-sdk/react";
import "./App.css";

const suggestions = [
  "What is the current water health?",
  "Summarize the latest sensor readings.",
  "Give me a quick status update.",
];

export default function App() {
  const [input, setInput] = useState("");
  const { messages, sendMessage, status, error } = useChat();
  const isBusy = status === "streaming" || status === "submitted";

  const submit = (e: React.FormEvent) => {
    e.preventDefault();

    const trimmed = input.trim();
    if (!trimmed || isBusy) return;

    sendMessage({ text: trimmed });
    setInput("");
  };

  return (
    <main className="chat-shell">
      <header className="chat-header">
        <div>
          <h1>Leafy Agent</h1>
        </div>
        <div className={`status-pill ${isBusy ? "busy" : "ready"}`}>
          {isBusy ? "Working" : "Ready"}
        </div>
      </header>

      <section className="message-list" aria-live="polite">
        {messages.length === 0 ? (
          <div className="welcome-panel">
            <h2>Ask about your water system</h2>
            <p>
              Check health, review sensor trends, and get a quick summary of the
              latest conditions.
            </p>

            <div className="suggestion-row">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className="suggestion-button"
                  onClick={() => setInput(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <article
              key={message.id}
              className={`message-row ${message.role === "user" ? "user" : "assistant"}`}
            >
              <div className="message-bubble">
                <span className="message-role">{message.role === "user" ? "You" : "Assistant"}</span>
                <div className="message-content">
                  {message.parts.map((part, i) =>
                    part.type === "text" ? <p key={`${message.id}-${i}`}>{part.text}</p> : null
                  )}
                </div>
              </div>
            </article>
          ))
        )}

        {isBusy && (
          <article className="message-row assistant">
            <div className="message-bubble pending">
              <span className="message-role">Assistant</span>
              <div className="message-content">
                <p>Thinking…</p>
              </div>
            </div>
          </article>
        )}
      </section>

      <form className="composer" onSubmit={submit}>
        <label className="sr-only" htmlFor="chat-input">
          Message
        </label>
        <input
          id="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question here..."
          autoComplete="off"
        />

        <button type="submit" disabled={!input.trim() || isBusy}>
          {isBusy ? "Sending..." : "Send"}
        </button>
      </form>

      {error && <div className="error-banner">{error.message}</div>}
    </main>
  );
}