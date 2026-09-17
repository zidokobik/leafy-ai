import '@fontsource/space-grotesk'
import '@fontsource/ibm-plex-mono'
import { useState, useMemo } from "react";
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

/*
  AIActionLog
  -----------
  Displays the historical record of Leafy AI's decisions: routine actions,
  the plain-language reasoning behind each one, and system alerts.

  MOCK_LOG below stands in for real data. When the backend/API is ready,
  swap the useState initial value for a fetch, e.g.:

    const [entries, setEntries] = useState([]);
    useEffect(() => {
      fetch("/api/action-log")
        .then((res) => res.json())
        .then(setEntries);
    }, []);

  Each entry's shape (id, timestamp, level, category, title, reasoning,
  status, sensor) is the contract your backend/database should match.
*/

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

const LEVEL_STYLES = {
  alert: { accent: "var(--accent-alert)", Icon: AlertTriangle, label: "Alert" },
  action: { accent: "var(--accent-good)", Icon: CheckCircle2, label: "Action" },
  info: { accent: "var(--accent-info)", Icon: Clock, label: "Info" },
};

const CATEGORY_ICONS = {
  Irrigation: Droplets,
  Dosing: Droplets,
  Lighting: Sun,
  Monitoring: Camera,
  Spacing: Camera,
  Harvest: Sprout,
};

const FILTERS = ["All", "Actions", "Alerts", "Info"];

export default function AIActionLog() {
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
    []
  );

  return (
    <div className="leafy-root">
      <style>{`

        .leafy-root {
          --bg: #10170f;
          --panel: #161f18;
          --panel-border: #263229;
          --text: #e7ece4;
          --text-muted: #8fa38c;
          --accent-good: #7fe0a4;
          --accent-warn: #e3a94a;
          --accent-alert: #e2634a;
          --accent-info: #6fb4d9;
          --sans: 'Space Grotesk', system-ui, sans-serif;
          --mono: 'IBM Plex Mono', ui-monospace, monospace;

          background: var(--bg);
          color: var(--text);
          font-family: var(--sans);
          text-align: left;
          min-height: 100%;
          padding: 28px 20px 60px;
          box-sizing: border-box;
        }

        .leafy-root * { box-sizing: border-box; }

        .leafy-header {
          max-width: 880px;
          margin: 0 auto 22px;
        }

        .leafy-eyebrow {
          font-family: var(--mono);
          font-size: 12.5px;
          color: var(--text-muted);
          margin: 0 0 6px;
        }

        .leafy-title {
          font-size: 26px;
          font-weight: 700;
          color: var(--text);
          margin: 0 0 4px;
          letter-spacing: -0.01em;
        }

        .leafy-subtitle {
          color: var(--text-muted);
          font-size: 14.5px;
          margin: 0;
          max-width: 60ch;
          line-height: 1.5;
        }

        .leafy-summary {
          max-width: 880px;
          margin: 20px auto 18px;
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
        }

        .leafy-summary-item {
          background: var(--panel);
          border: 1px solid var(--panel-border);
          border-radius: 6px;
          padding: 12px 14px;
        }

        .leafy-summary-value {
          font-family: var(--mono);
          font-size: 20px;
          font-weight: 500;
        }

        .leafy-summary-label {
          font-size: 12.5px;
          color: var(--text-muted);
          margin-top: 2px;
        }

        .leafy-controls {
          max-width: 880px;
          margin: 0 auto 16px;
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          align-items: center;
        }

        .leafy-filters {
          display: flex;
          gap: 4px;
          background: var(--panel);
          border: 1px solid var(--panel-border);
          border-radius: 7px;
          padding: 3px;
        }

        .leafy-filter-btn {
          font-family: var(--sans);
          font-size: 13px;
          font-weight: 500;
          color: var(--text-muted);
          background: transparent;
          border: none;
          padding: 6px 12px;
          border-radius: 5px;
          cursor: pointer;
          transition: background 0.15s ease, color 0.15s ease;
        }

        .leafy-filter-btn.active {
          background: #223028;
          color: var(--text);
        }

        .leafy-search {
          flex: 1;
          min-width: 180px;
          display: flex;
          align-items: center;
          gap: 8px;
          background: var(--panel);
          border: 1px solid var(--panel-border);
          border-radius: 7px;
          padding: 8px 12px;
        }

        .leafy-search input {
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          color: var(--text);
          font-family: var(--sans);
          font-size: 13.5px;
        }

        .leafy-search input::placeholder { color: var(--text-muted); }

        .leafy-log {
          max-width: 880px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .leafy-entry {
          background: var(--panel);
          border: 1px solid var(--panel-border);
          border-left: 3px solid var(--row-accent, var(--panel-border));
          border-radius: 6px;
          overflow: hidden;
        }

        .leafy-entry-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 14px;
          cursor: pointer;
        }

        .leafy-entry-icon {
          width: 30px;
          height: 30px;
          border-radius: 6px;
          background: #1c2820;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .leafy-entry-main {
          flex: 1;
          min-width: 0;
        }

        .leafy-entry-title {
          font-size: 14.5px;
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .leafy-entry-meta {
          font-family: var(--mono);
          font-size: 12px;
          color: var(--text-muted);
          margin-top: 2px;
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .leafy-status {
          font-family: var(--mono);
          font-size: 11.5px;
          padding: 3px 8px;
          border-radius: 4px;
          background: #1c2820;
          color: var(--text-muted);
          white-space: nowrap;
        }

        .leafy-chevron {
          color: var(--text-muted);
          transition: transform 0.15s ease;
          flex-shrink: 0;
        }

        .leafy-chevron.open { transform: rotate(180deg); }

        .leafy-entry-detail {
          padding: 0 14px 16px 56px;
        }

        .leafy-entry-detail p {
          font-size: 13.5px;
          line-height: 1.55;
          color: #cbd6c6;
          margin: 0 0 10px;
          max-width: 68ch;
        }

        .leafy-entry-sensor {
          font-family: var(--mono);
          font-size: 12px;
          color: var(--text-muted);
        }

        .leafy-empty {
          max-width: 880px;
          margin: 40px auto;
          text-align: center;
          color: var(--text-muted);
          font-size: 14px;
        }

        @media (max-width: 560px) {
          .leafy-summary { grid-template-columns: 1fr; }
          .leafy-entry-detail { padding-left: 14px; }
        }
      `}</style>

      <div className="leafy-header">
        <p className="leafy-eyebrow">Leafy AI</p>
        <h1 className="leafy-title">Action log & reasoning</h1>
        <p className="leafy-subtitle">
          Every recommendation, automatic action, and alert the agent has raised for the
          basil farm, with the plain-language reasoning behind each one.
        </p>
      </div>

      <div className="leafy-summary">
        <div className="leafy-summary-item">
          <div className="leafy-summary-value" style={{ color: "var(--accent-alert)" }}>
            {counts.alerts}
          </div>
          <div className="leafy-summary-label">Alerts raised</div>
        </div>
        <div className="leafy-summary-item">
          <div className="leafy-summary-value" style={{ color: "var(--accent-warn)" }}>
            {counts.pending}
          </div>
          <div className="leafy-summary-label">Awaiting review</div>
        </div>
        <div className="leafy-summary-item">
          <div className="leafy-summary-value" style={{ color: "var(--accent-good)" }}>
            {counts.autoApplied}
          </div>
          <div className="leafy-summary-label">Auto-applied</div>
        </div>
      </div>

      <div className="leafy-controls">
        <div className="leafy-filters">
          {FILTERS.map((f) => (
            <button
              key={f}
              className={`leafy-filter-btn ${activeFilter === f ? "active" : ""}`}
              onClick={() => setActiveFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="leafy-search">
          <Search size={15} color="var(--text-muted)" />
          <input
            placeholder="Search actions, categories, reasoning…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="leafy-log">
        {filtered.length === 0 && (
          <div className="leafy-empty">No log entries match that search or filter.</div>
        )}

        {filtered.map((entry) => {
          const { accent, Icon: LevelIcon } = LEVEL_STYLES[entry.level as keyof typeof LEVEL_STYLES];
          const CategoryIcon = CATEGORY_ICONS[entry.category as keyof typeof CATEGORY_ICONS] || Sprout;
          const isOpen = expandedId === entry.id;

          return (
            <div
              key={entry.id}
              className="leafy-entry"
              style={{ "--row-accent": accent } as React.CSSProperties}
            >
              <div
                className="leafy-entry-row"
                onClick={() => setExpandedId(isOpen ? null : entry.id)}
              >
                <div className="leafy-entry-icon">
                  <CategoryIcon size={15} color={accent} />
                </div>
                <div className="leafy-entry-main">
                  <div className="leafy-entry-title">{entry.title}</div>
                  <div className="leafy-entry-meta">
                    <span>{entry.timestamp}</span>
                    <span>·</span>
                    <span>{entry.category}</span>
                  </div>
                </div>
                <span className="leafy-status">{entry.status}</span>
                <LevelIcon size={14} color={accent} />
                <ChevronDown size={16} className={`leafy-chevron ${isOpen ? "open" : ""}`} />
              </div>

              {isOpen && (
                <div className="leafy-entry-detail">
                  <p>{entry.reasoning}</p>
                  {entry.sensor && (
                    <div className="leafy-entry-sensor">{entry.sensor}</div>
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