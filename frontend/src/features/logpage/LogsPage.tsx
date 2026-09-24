import React, { useState, useMemo } from "react";
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

// --- Mock Data ---
const MOCK_LOG = [
  {
    id: 1,
    timestamp: "Today, 14:32",
    level: "alert",
    category: "Dosing",
    title: "EC levels above safe range",
    reasoning:
      "EC readings rose across three consecutive samples (18 minutes apart), ruling out a single sensor glitch. This trend crossed the upper bound of the approved operating range for current-stage basil, so automatic dosing was paused rather than issued, since dosing is a medium-risk action requiring trend confirmation and human sign-off.",
    status: "Pending review",
    sensor: "EC 2.6 mS/cm (limit 2.2 mS/cm)",
  },
  {
    id: 2,
    timestamp: "Today, 13:05",
    level: "action",
    category: "Lighting",
    title: "Extended photoperiod on Level 2",
    reasoning:
      "Camera analysis showed slower leaf expansion on Level 2 compared with Levels 1 and 3 over the past 4 days, while temperature and EC were within range. Since lighting is a low-risk, per-level action already cleared for automatic control, the photoperiod was extended by 45 minutes without requiring approval.",
    status: "Auto-applied",
    sensor: "Leaf area +6% below Level 1/3 average",
  },
  {
    id: 3,
    timestamp: "Today, 11:47",
    level: "action",
    category: "Spacing",
    title: "Recommended telescopic channel expansion",
    reasoning:
      "Canopy overlap in the camera feed exceeded the crowding threshold for this growth stage on Level 1. Because channel expansion is a manual physical action, Leafy AI can only recommend it, not perform it. The recommendation is queued for a technician to carry out during the next farm visit.",
    status: "Awaiting manual action",
    sensor: "Canopy overlap 34% (threshold 25%)",
  },
  {
    id: 4,
    timestamp: "Yesterday, 19:20",
    level: "alert",
    category: "Monitoring",
    title: "Possible early nutrient deficiency detected",
    reasoning:
      "Leaf-colour analysis on 3 plants in Level 3 showed a yellowing pattern consistent with early nitrogen deficiency, but confidence was below the threshold needed to trigger a dosing recommendation. Flagged for human visual confirmation rather than acted on automatically, in line with the rule that medium/high-risk calls need trend or human confirmation.",
    status: "Acknowledged",
    sensor: "Vision confidence 62% (action threshold 80%)",
  },
  {
    id: 5,
    timestamp: "Yesterday, 09:14",
    level: "action",
    category: "Irrigation",
    title: "Irrigation cycle shortened",
    reasoning:
      "Root zone images and EC trend together suggested mild overwatering rather than nutrient excess. Since irrigation is shared across the whole farm and classed as higher-risk, the shortened cycle was only applied after a supervisor approved it through the dashboard.",
    status: "Approved",
    sensor: "EC stable, substrate visibly saturated",
  },
  {
    id: 6,
    timestamp: "2 days ago, 16:41",
    level: "info",
    category: "Harvest",
    title: "Harvest outcome recorded — Level 1, Batch 7",
    reasoning:
      "Yield and leaf-quality data for Batch 7 were logged against the growing routine that produced them, so future recommendations for similar conditions can be weighted by this outcome rather than treated as a fresh guess each time.",
    status: "Logged",
    sensor: "Yield 1.4 kg, 92% Grade A leaves",
  },
  {
    id: 7,
    timestamp: "2 days ago, 08:03",
    level: "action",
    category: "Lighting",
    title: "Fan speed increased on Level 3",
    reasoning:
      "Temperature and humidity sensors on Level 3 both trended upward for over an hour, consistent with reduced airflow rather than a faulty reading. Fan control is a low-risk, per-level action, so the increase was applied automatically and logged.",
    status: "Auto-applied",
    sensor: "28.4°C / 76% RH (target ≤26°C / 70% RH)",
  },
  {
    id: 8,
    timestamp: "3 days ago, 12:56",
    level: "alert",
    category: "Dosing",
    title: "Dosing command blocked by safety layer",
    reasoning:
      "A proposed pH correction would have exceeded the maximum per-cycle dosing limit hard-coded into the safety layer. The command was rejected before reaching the relay pumps, and a smaller, compliant correction was proposed in its place for approval.",
    status: "Rejected by safety layer",
    sensor: "pH 5.4 → requested correction 0.9 (limit 0.4/cycle)",
  },
];

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

const FILTERS = ["All", "Actions", "Alerts", "Info"];

export function LogsPage() {
  const [activeFilter, setActiveFilter] = useState("All");
  const [query, setQuery] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const filtered = useMemo(() => {
    return MOCK_LOG.filter((entry) => {
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
        entry.reasoning.toLowerCase().includes(q);

      return matchesFilter && matchesQuery;
    });
  }, [activeFilter, query]);

  const counts = useMemo(
    () => ({
      alerts: MOCK_LOG.filter((e) => e.level === "alert").length,
      pending: MOCK_LOG.filter((e) => e.status === "Pending review").length,
      autoApplied: MOCK_LOG.filter((e) => e.status === "Auto-applied").length,
    }),
    [],
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
          Every recommendation, automatic action, and alert the agent has raised
          for the basil farm, with the plain-language reasoning behind each one.
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
          <div className="font-mono text-2xl font-medium text-red-500">
            {counts.alerts}
          </div>
          <div className="text-sm text-gray-500 mt-1">Alerts raised</div>
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
          <div className="text-sm text-gray-500 mt-1">Auto-applied</div>
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

      {/* Log Entries */}
      <div className="flex flex-col gap-3">
        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm">
            No log entries match that search or filter.
          </div>
        )}

        {filtered.map((entry) => {
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
                onClick={() => setExpandedId(isOpen ? null : entry.id)}
              >
                <CategoryIcon className="w-5 h-5 ${style.color}" />

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
