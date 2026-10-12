import React, { useState, useMemo } from "react";
import type { ProposalStatus } from "@/api/proposals";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  PlugZap,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ChevronDown,
  Search,
} from "lucide-react";
import { ProposalActionButtons, ProposalConfirmDialog } from "../proposals/ProposalActions";
import { formatDuration, isExpired, proposalStatusMeta } from "../proposals/proposalMeta";
import { useNow } from "../proposals/useNow";
import { useProposalActions } from "../proposals/useProposalActions";
import { useProposals } from "../proposals/useProposals";

type LogLevel = "alert" | "action" | "info";

const LEVEL_STYLES: Record<
  LogLevel,
  { color: string; bg: string; border: string; Icon: React.ElementType }
> = {
  alert: {
    color: "text-red-500",
    bg: "bg-red-100 dark:bg-red-900/30",
    border: "border-red-500",
    Icon: AlertTriangle,
  },
  action: {
    color: "text-emerald-500",
    bg: "bg-emerald-100 dark:bg-emerald-900/30",
    border: "border-emerald-500",
    Icon: CheckCircle2,
  },
  info: {
    color: "text-blue-500",
    bg: "bg-blue-100 dark:bg-blue-900/30",
    border: "border-blue-500",
    Icon: Clock,
  },
};

const FILTERS = ["All", "Awaiting review", "Actions", "Failed"];

const PAGE_SIZE = 20;

function formatTime(value: string) {
  return new Date(value).toLocaleString("en-AU", { timeZone: "Australia/Melbourne", timeZoneName: "short" });
}

function levelOf(status: ProposalStatus): LogLevel {
  if (status === "failed") return "alert";
  if (status === "running" || status === "completed" || status === "stopped") return "action";
  return "info";
}

export function LogsPage() {
  const [activeFilter, setActiveFilter] = useState("All");
  const [query, setQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  const logs = useProposals({ limit: PAGE_SIZE, offset });
  const actions = useProposalActions(logs.refresh);
  const now = useNow();
  const entries = useMemo(() => logs.proposals.map((proposal) => {
    const status: ProposalStatus = isExpired(proposal, now) ? "expired" : proposal.status;
    return {
      id: proposal.id,
      timestamp: formatTime(proposal.createdAt),
      level: levelOf(status),
      category: proposal.scheduleId ? "Agent proposal · scheduled run" : "Agent proposal",
      title: `Switch on ${proposal.deviceName} for ${formatDuration(proposal.durationSeconds)}`,
      reasoning: proposal.reason,
      statusKey: status,
      status: proposalStatusMeta[status].label,
      proposal,
    };
  }), [logs.proposals, now]);

  const filtered = useMemo(() => {
    return entries.filter((entry) => {
      const matchesFilter =
        activeFilter === "All" ||
        (activeFilter === "Awaiting review" && entry.statusKey === "pending") ||
        (activeFilter === "Actions" && entry.level === "action") ||
        (activeFilter === "Failed" && entry.level === "alert");

      const q = query.trim().toLowerCase();
      const matchesQuery =
        q === "" ||
        entry.title.toLowerCase().includes(q) ||
        entry.category.toLowerCase().includes(q) ||
        entry.reasoning.toLowerCase().includes(q) ||
        (entry.proposal.resultMessage ?? "").toLowerCase().includes(q);

      return matchesFilter && matchesQuery;
    });
  }, [activeFilter, query, entries]);

  const counts = useMemo(
    () => ({
      pending: entries.filter((e) => e.statusKey === "pending").length,
      running: entries.filter((e) => e.statusKey === "running").length,
      failed: entries.filter((e) => e.statusKey === "failed").length,
    }),
    [entries],
  );

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <p className="font-mono text-xs text-gray-500 uppercase tracking-wider mb-2">
          Leafy AI
        </p>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Action log & reasoning
        </h1>
        <p className="text-gray-500 text-base max-w-2xl">
          Device runs proposed by the agent, how each was reviewed, and how
          each run ended. Times are Melbourne time.
        </p>
      </div>

      {(logs.error || actions.error) && <Alert variant="destructive"><AlertDescription>{actions.error || logs.error}</AlertDescription></Alert>}
      {actions.notice && <Alert role="status"><AlertDescription>{actions.notice}</AlertDescription></Alert>}
      <div className="mb-4 flex items-center gap-3"><Button variant="outline" disabled={actions.busy || logs.status === "loading"} onClick={logs.refresh}>Refresh logs</Button><p className="text-sm text-muted-foreground">Counts, search and filters apply to this page of proposals.</p></div>
      {logs.status === "loading" && <p role="status">Loading logs...</p>}
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
          <div className="font-mono text-2xl font-medium text-amber-500">
            {counts.pending}
          </div>
          <div className="text-sm text-gray-500 mt-1">Awaiting review</div>
        </div>
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
          <div className="font-mono text-2xl font-medium text-emerald-500">
            {counts.running}
          </div>
          <div className="text-sm text-gray-500 mt-1">Running now</div>
        </div>
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
          <div className="font-mono text-2xl font-medium text-red-500">
            {counts.failed}
          </div>
          <div className="text-sm text-gray-500 mt-1">Failed</div>
        </div>
      </div>

      {/* Controls: Search & Filters */}
      <div className="flex flex-col justify-between items-start gap-4 mb-8">
        <div className="flex flex-wrap items-start gap-2 w-full lg:w-auto">
          {FILTERS.map((f) => (
            <button
              key={f}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors shadow-sm ${
                activeFilter === f
                  ? "bg-white-900 text-black order border border-black"
                  : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
              }`}
              onClick={() => setActiveFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="flex items-center w-full lg:max-w-md h-10 px-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm focus-within:ring-2 focus-within:ring-purple-500 transition-shadow">
          {/* Changed mr-2.5 to mr-4 to push the text further to the right */}
          <Search className="w-4 h-4 text-gray-400" />

          <input
            type="text"
            placeholder=" Search devices, reasoning, results…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 w-full bg-transparent border-none outline-none text-sm text-gray-900 dark:text-white placeholder:text-gray-400"
          />
        </div>
      </div>

      <div className="mb-4 flex items-center gap-3"><Button variant="outline" disabled={actions.busy || logs.status === "loading" || offset === 0} onClick={() => setOffset(offset - PAGE_SIZE)}>Previous</Button><span>Page {offset / PAGE_SIZE + 1}</span><Button variant="outline" disabled={actions.busy || logs.status !== "ready" || logs.proposals.length < PAGE_SIZE} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</Button></div>
      {/* Log Entries */}
      <div className="flex flex-col gap-3">
        {logs.status !== "loading" && filtered.length === 0 && (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm">
            {entries.length === 0 ? "No device proposals yet." : "No log entries match that search or filter."}
          </div>
        )}

        {logs.status !== "loading" && filtered.map((entry) => {
          const style = LEVEL_STYLES[entry.level];
          const LevelIcon = style.Icon;
          const isOpen = expandedId === entry.id;
          const { proposal } = entry;

          return (
            <div
              key={entry.id}
              className={`bg-white rounded-xl overflow-hidden shadow-sm border-l-4 ${style.border}`}
            >
              <div
                className="flex items-center gap-4 p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                role="button"
                tabIndex={0}
                aria-expanded={isOpen}
                onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setExpandedId(isOpen ? null : entry.id); } }}
                onClick={() => setExpandedId(isOpen ? null : entry.id)}
              >
                <PlugZap className={`size-5 ${style.color}`} />

                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-900 dark:text-white truncate">
                    {entry.title}
                  </div>
                  <div className="font-mono text-xs text-gray-500 mt-1 flex gap-2 flex-wrap">
                    <span>{entry.timestamp}</span>
                    <span>·</span>
                    <span>{entry.category}</span>
                  </div>
                </div>

                <div className="hidden sm:block font-mono text-xs px-2.5 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 whitespace-nowrap">
                  {entry.status}
                </div>
                <LevelIcon
                  className={`w-4 h-4 hidden sm:block ${style.color}`}
                />
                <ChevronDown
                  className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
                />
              </div>

              {isOpen && (
                <div className="px-4 pb-5 pl-[4.5rem]">
                  {/* Status badge for mobile views */}
                  <div className="sm:hidden font-mono text-xs inline-block px-2.5 py-1 mb-3 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                    Status: {entry.status}
                  </div>

                  <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed mb-3 max-w-3xl">
                    {entry.reasoning}
                  </p>
                  <div className="mb-3 flex flex-col gap-2 break-words text-sm text-muted-foreground">
                    <p>Device: {proposal.deviceName}{proposal.deviceId === null && " (since deleted)"}</p>
                    {proposal.resultMessage && <p>{proposal.resultMessage}</p>}
                    {entry.statusKey === "pending" && <p>Review by: {formatTime(proposal.expiresAt)}</p>}
                    {proposal.reviewedAt && <p>Reviewed: {formatTime(proposal.reviewedAt)}{proposal.reviewerEmail && ` by ${proposal.reviewerEmail}`}</p>}
                    {proposal.startedAt && <p>Switched on: {formatTime(proposal.startedAt)}</p>}
                    {proposal.status === "running" && proposal.endsAt && <p>Switches off: {formatTime(proposal.endsAt)}</p>}
                    {proposal.finishedAt && <p>Finished: {formatTime(proposal.finishedAt)}</p>}
                  </div>
                  <div className="mb-3 flex gap-2">
                    <ProposalActionButtons proposal={proposal} now={now} busy={actions.busy} onAction={actions.request} />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <ProposalConfirmDialog
        confirmation={actions.confirmation}
        open={actions.confirmOpen}
        busy={actions.busy}
        onConfirm={actions.confirm}
        onCancel={actions.cancel}
      />
    </div>
  );
}
