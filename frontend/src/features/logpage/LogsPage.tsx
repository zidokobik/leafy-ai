import React, { useState, useMemo, useEffect, useRef } from "react";
import { safetyApi } from "@/api/safety";
import { safetyError, useSafetyList } from "../safety/useSafetyList";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Droplets,
  Sun,
  Camera,
  Sprout,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ChevronDown,
  Search,
} from "lucide-react";

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

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  Irrigation: Droplets,
  Dosing: Droplets,
  Lighting: Sun,
  Monitoring: Camera,
  Spacing: Camera,
  Harvest: Sprout,
};

const FILTERS = ["All", "Actions", "Alerts"];

export function LogsPage() {
  const [activeFilter, setActiveFilter] = useState("All");
  const [query, setQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const logs = useSafetyList(safetyApi.commands);
  const [now, setNow] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const [actionError, setActionError] = useState("");
  const [feedback, setFeedback] = useState("");
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const entries = useMemo(() => logs.items.map((request) => {
    const expired = !request.startedAt && ["pending_approval", "approved"].includes(request.status) && Date.parse(request.expiresAt) <= now;
    const status = expired ? "expired" : request.status;
    return {
      id: request.requestId,
      timestamp: new Date(request.createdAt).toLocaleString("en-AU", { timeZone: "Australia/Melbourne", timeZoneName: "short" }),
      level: (["blocked", "failed", "unknown"].includes(status) ? "alert" : "action") as LogLevel,
      category: "Device operation",
      title: `Run device for ${request.durationSeconds} seconds`,
      reasoning: request.reason,
      status: status === "pending_approval" ? "Pending review" : status.replaceAll("_", " "),
      sensor: null,
      request,
      expired,
    };
  }), [logs.items, now]);

  async function reviewRequest(id: string, action: "approve" | "reject") {
    if (inFlight.current) return;
    const request = logs.items.find((item) => item.requestId === id);
    if (!request || request.status !== "pending_approval" || Date.parse(request.expiresAt) <= now) return;
    if (!window.confirm(`${action === "approve" ? "Approve" : "Reject"} this operation? Approval does not execute hardware.`)) return;
    inFlight.current = true;
    setBusy(true); setActionError(""); setFeedback("");
    try {
      const result = await safetyApi.review(id, action);
      setFeedback(`Request ${result.status.replaceAll("_", " ")}. ${result.resultMessage ?? ""}`);
    } catch (error) {
      setActionError(`${safetyError(error)} Check the refreshed record before retrying.`);
    } finally {
      inFlight.current = false; setBusy(false); logs.refresh();
    }
  }

  const filtered = useMemo(() => {
    return entries.filter((entry) => {
      const matchesFilter =
        activeFilter === "All" ||
        (activeFilter === "Actions" && entry.level === "action") ||
        (activeFilter === "Alerts" && entry.level === "alert") ||
        (activeFilter === "Info" && entry.level === "info");

      const q = query.trim().toLowerCase();
      const matchesQuery =
        q === "" ||
        entry.title.toLowerCase().includes(q) ||
        entry.category.toLowerCase().includes(q) ||
        entry.request.deviceId.toLowerCase().includes(q) ||
        entry.reasoning.toLowerCase().includes(q);

      return matchesFilter && matchesQuery;
    });
  }, [activeFilter, query, entries]);

  const counts = useMemo(
    () => ({
      alerts: entries.filter((e) => e.level === "alert").length,
      pending: entries.filter((e) => e.status === "Pending review").length,
      autoApplied: entries.filter((e) => e.status === "approved").length,
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
          Stored operation requests, safety outcomes, and human reviews.
          Hardware execution is not connected. Times are Melbourne time.
        </p>
      </div>

      {(logs.error || actionError) && <Alert variant="destructive"><AlertDescription>{actionError || logs.error}</AlertDescription></Alert>}
      {feedback && <Alert role="status"><AlertDescription>{feedback}</AlertDescription></Alert>}
      <div className="mb-4 flex items-center gap-3"><Button variant="outline" disabled={busy || logs.status === "loading"} onClick={logs.refresh}>Refresh logs</Button><p className="text-sm text-muted-foreground">Counts, search and filters apply to this page of operation requests.</p></div>
      {logs.status === "loading" && <p role="status">Loading logs...</p>}
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
          <div className="font-mono text-2xl font-medium text-red-500">
            {counts.alerts}
          </div>
          <div className="text-sm text-gray-500 mt-1">Blocked / failed requests</div>
        </div>
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
          <div className="font-mono text-2xl font-medium text-amber-500">
            {counts.pending}
          </div>
          <div className="text-sm text-gray-500 mt-1">Awaiting review</div>
        </div>
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
          <div className="font-mono text-2xl font-medium text-emerald-500">
            {counts.autoApplied}
          </div>
          <div className="text-sm text-gray-500 mt-1">Approved, not executed</div>
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
            placeholder=" Search actions, categories, reasoning…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 w-full bg-transparent border-none outline-none text-sm text-gray-900 dark:text-white placeholder:text-gray-400"
          />
        </div>
      </div>

      <div className="mb-4 flex items-center gap-3"><Button variant="outline" disabled={busy || logs.status === "loading" || logs.offset === 0} onClick={() => logs.page(logs.offset - 20)}>Previous</Button><span>Page {logs.offset / 20 + 1}</span><Button variant="outline" disabled={busy || logs.status !== "ready" || logs.items.length < 20} onClick={() => logs.page(logs.offset + 20)}>Next</Button></div>
      {/* Log Entries */}
      <div className="flex flex-col gap-3">
        {logs.status === "ready" && filtered.length === 0 && (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm">
            No log entries match that search or filter.
          </div>
        )}

        {logs.status === "ready" && filtered.map((entry) => {
          const style = LEVEL_STYLES[entry.level as LogLevel];
          const CategoryIcon = CATEGORY_ICONS[entry.category] || Sprout;
          const LevelIcon = style.Icon;
          const isOpen = expandedId === entry.id;

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
                <CategoryIcon className={`size-5 ${style.color}`} />

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
                    <p>Device UUID: {entry.request.deviceId}</p>
                    <p>{entry.expired ? "Request expired before execution." : entry.request.resultMessage}</p>
                    <p>Expires: {new Date(entry.request.expiresAt).toLocaleString("en-AU", { timeZone: "Australia/Melbourne", timeZoneName: "short" })}</p>
                    {entry.request.reviewedAt && <p>Reviewed: {new Date(entry.request.reviewedAt).toLocaleString("en-AU", { timeZone: "Australia/Melbourne", timeZoneName: "short" })}</p>}
                    {entry.request.reviewedBy && <p>Reviewer UUID: {entry.request.reviewedBy}</p>}
                  </div>
                  <div className="mb-3 flex gap-2">
                    <Button disabled={busy || entry.status !== "Pending review"} onClick={() => void reviewRequest(entry.id, "approve")}>Approve</Button>
                    <Button variant="outline" disabled={busy || entry.status !== "Pending review"} onClick={() => void reviewRequest(entry.id, "reject")}>Reject</Button>
                  </div>

                  {entry.sensor && (
                    <div className="font-mono text-xs text-gray-500 bg-gray-50 dark:bg-gray-800/50 inline-flex px-2 py-1 rounded border border-gray-100 dark:border-gray-800">
                      Sensor context: {entry.sensor}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
