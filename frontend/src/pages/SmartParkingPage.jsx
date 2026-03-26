import { useEffect, useState } from "react";
import { formatPlateDisplay } from "../utils/plate";
import "./smart-parking.css";

const rawApiBase = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const API_PREFIX = rawApiBase ? `${rawApiBase}/api/anpr` : "/api/anpr";

const OCR_MODES = {
  trained: "Moroccan Plate (Custom OCR)",
  tesseract: "General Plate (Tesseract-OCR)",
};

const QUICK_QUESTIONS = [
  "Qui est entré dans le parking aujourd’hui ?",
  "Quels véhicules ont accédé au parking aujourd’hui ?",
  "Combien d’employés sont actuellement présents ?",
  "Quels employés sont actuellement dans le parking ?",
  "Afficher les 10 derniers accès au parking",
  "Quelles plaques sont autorisées ?",
  "Quels véhicules ont été refusés ?",
  "Qui arrive souvent en retard ?",
];

const REPORT_TYPES = [
  { value: "daily", label: "Quotidien" },
  { value: "weekly", label: "Hebdomadaire" },
  { value: "monthly", label: "Mensuel" },
  { value: "yearly", label: "Annuel" },
  { value: "custom", label: "Personnalise" },
];

const reportTypeLabel = (value) => REPORT_TYPES.find((item) => item.value === value)?.label || value;

const STATUS_VALUES = ["AUTHORIZED", "BLACKLISTED", "UNKNOWN", "DENIED"];
const LINE_KEYS = ["owner_name", "plate_number", "status", "entry_time", "exit_time", "detected_at", "vehicle_type"];

const formatTimestamp = (value) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const formatMinutes = (value) => {
  if (value === null || value === undefined) return "-";
  const total = Math.round(Number(value));
  if (Number.isNaN(total)) return "-";
  const hours = Math.floor(total / 60);
  const minutes = total % 60;
  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`;
};

const toDateInput = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
};

const getIsoWeek = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return { year: new Date().getFullYear(), week: 1 };
  const target = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNumber = target.getUTCDay() || 7;
  target.setUTCDate(target.getUTCDate() + 4 - dayNumber);
  const yearStart = new Date(Date.UTC(target.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((target - yearStart) / 86400000 + 1) / 7);
  return { year: target.getUTCFullYear(), week };
};

const normalizeQuestion = (value) => {
  if (!value) return "";
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/â€™/g, "'")
    .replace(/[’']/g, "'")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
};

const buildQuickSpecs = () => {
  const specs = new Map();
  const add = (question, columns) => {
    specs.set(normalizeQuestion(question), { question, columns });
  };

  add(QUICK_QUESTIONS[0], [
    { label: "Owner", key: "owner_name" },
    { label: "Plate", key: "plate_number" },
    { label: "Entry", key: "entry_time", format: formatTimestamp },
    { label: "Status", key: "status", badge: true },
  ]);
  add(QUICK_QUESTIONS[1], [
    { label: "Plate", key: "plate_number" },
    { label: "Entry", key: "entry_time", format: formatTimestamp },
    { label: "Status", key: "status", badge: true },
  ]);
  add(QUICK_QUESTIONS[2], [
    { label: "Total", key: "count", numeric: true },
  ]);
  add(QUICK_QUESTIONS[3], [
    { label: "Owner", key: "owner_name" },
    { label: "Plate", key: "plate_number" },
    { label: "Entry", key: "entry_time", format: formatTimestamp },
    { label: "Status", key: "status", badge: true },
  ]);
  add(QUICK_QUESTIONS[4], [
    { label: "Plate", key: "plate_number" },
    { label: "Entry", key: "entry_time", format: formatTimestamp },
    { label: "Exit", key: "exit_time", format: formatTimestamp },
    { label: "Status", key: "status", badge: true },
  ]);
  add(QUICK_QUESTIONS[5], [
    { label: "Plate", key: "plate_number" },
    { label: "Owner", key: "owner_name" },
    { label: "Department", key: "vehicle_type" },
    { label: "Status", key: "status", badge: true },
  ]);
  add(QUICK_QUESTIONS[6], [
    { label: "Plate", key: "plate_number" },
    { label: "Owner", key: "owner_name" },
    { label: "Entry", key: "entry_time", format: formatTimestamp },
    { label: "Status", key: "status", badge: true },
  ]);
  add(QUICK_QUESTIONS[7], [
    { label: "Owner", key: "owner_name" },
    { label: "Plate", key: "plate_number" },
    { label: "Entry", key: "entry_time", format: formatTimestamp },
  ]);

  return specs;
};

const QUICK_SPECS = buildQuickSpecs();

const isVideoFile = (value) => {
  if (!value) return false;
  if (value.type && value.type.startsWith("video/")) return true;
  const ext = value.name.split(".").pop()?.toLowerCase();
  return ["mp4", "avi", "mov"].includes(ext || "");
};

export default function SmartParkingPage() {
  const today = new Date();
  const todayIso = toDateInput(today);
  const todayWeek = getIsoWeek(today);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [ocrMode, setOcrMode] = useState("trained");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState({ blacklisted: [], unknown: [] });
  const [stats, setStats] = useState(null);
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [reportType, setReportType] = useState("daily");
  const [reportDate, setReportDate] = useState(todayIso);
  const [reportYear, setReportYear] = useState(todayWeek.year);
  const [reportWeek, setReportWeek] = useState(todayWeek.week);
  const [reportMonth, setReportMonth] = useState(today.getMonth() + 1);
  const [reportStartDate, setReportStartDate] = useState(todayIso);
  const [reportEndDate, setReportEndDate] = useState(todayIso);
  const [reportPreview, setReportPreview] = useState(null);
  const [reportHistory, setReportHistory] = useState([]);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const loadLogs = async () => {
    const res = await fetch(`${API_PREFIX}/logs?limit=12`);
    const data = await res.json();
    setLogs(data.items || []);
  };

  const loadAlerts = async () => {
    const res = await fetch(`${API_PREFIX}/alerts?limit=8`);
    const data = await res.json();
    setAlerts(data || { blacklisted: [], unknown: [] });
  };

  const loadStats = async () => {
    const res = await fetch(`${API_PREFIX}/stats`);
    const data = await res.json();
    setStats(data);
  };

  const loadReports = async () => {
    const res = await fetch(`${API_PREFIX}/reports?limit=12`);
    const data = await res.json().catch(() => []);
    setReportHistory(Array.isArray(data) ? data : []);
  };

  useEffect(() => {
    loadLogs();
    loadAlerts();
    loadStats();
    loadReports();
    const interval = window.setInterval(() => {
      loadLogs();
      loadAlerts();
      loadStats();
    }, 10000);
    return () => window.clearInterval(interval);
  }, []);

  const resetTransient = () => {
    setError("");
  };

  const resetReportError = () => {
    setReportError("");
  };

  const buildReportPayload = () => {
    resetReportError();
    if (reportType === "daily") {
      if (!reportDate) return null;
      return { report_type: reportType, date: reportDate };
    }
    if (reportType === "weekly") {
      return { report_type: reportType, year: Number(reportYear), week: Number(reportWeek) };
    }
    if (reportType === "monthly") {
      return { report_type: reportType, year: Number(reportYear), month: Number(reportMonth) };
    }
    if (reportType === "yearly") {
      return { report_type: reportType, year: Number(reportYear) };
    }
    if (reportType === "custom") {
      if (!reportStartDate || !reportEndDate) return null;
      return { report_type: reportType, start_date: reportStartDate, end_date: reportEndDate };
    }
    return null;
  };

  const previewReport = async () => {
    const payload = buildReportPayload();
    if (!payload) {
      setReportError("Champs manquants pour la previsualisation.");
      return;
    }
    setReportLoading(true);
    try {
      const res = await fetch(`${API_PREFIX}/reports/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Previsualisation impossible.");
      }
      setReportPreview(data);
    } catch (err) {
      setReportError(err.message || "Erreur de previsualisation.");
    } finally {
      setReportLoading(false);
    }
  };

  const generateReportPdf = async () => {
    const payload = buildReportPayload();
    if (!payload) {
      setReportError("Champs manquants pour la generation.");
      return;
    }
    setReportLoading(true);
    try {
      const res = await fetch(`${API_PREFIX}/reports/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Generation impossible.");
      }
      setReportPreview((prev) => (prev ? { ...prev, download_url: data.download_url } : data));
      await loadReports();
    } catch (err) {
      setReportError(err.message || "Erreur de generation.");
    } finally {
      setReportLoading(false);
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!file) {
      setError("Select an image or video first.");
      return;
    }
    setLoading(true);
    resetTransient();
    try {
      const isVideo = isVideoFile(file);
      const body = new FormData();
      body.append(isVideo ? "video" : "image", file);
      body.append("ocr_mode", ocrMode);
      const res = await fetch(`${API_PREFIX}/detect`, {
        method: "POST",
        body,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Detection failed.");
      }
      setResult(data);
      await Promise.all([loadLogs(), loadAlerts(), loadStats()]);
    } catch (err) {
      setError(err.message || "Unexpected error.");
    } finally {
      setLoading(false);
    }
  };

  const gateState = result?.decision?.gate || "CLOSED";
  const gateLabel = gateState === "OPEN" ? "Gate Opened" : "Gate Closed";

  const parseAssistantRecords = (content) => {
    if (!content) return { header: "", records: [] };
    const parts = content.split(" - ").map((item) => item.trim()).filter(Boolean);
    if (parts.length <= 1) return { header: "", records: [] };
    let header = "";
    if (parts[0].includes(":") && parts[0].length < 120) {
      header = parts.shift();
    }
    const records = [];
    const isoRegex = /\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?/;
    const frRegex = /\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}/;

    for (const part of parts) {
      const upper = part.toUpperCase();
      const status = STATUS_VALUES.find((value) => upper.includes(value));
      if (!status) continue;
      const statusIndex = upper.indexOf(status);
      const plate = part.slice(0, statusIndex).trim();
      const timeMatch = part.match(isoRegex) || part.match(frRegex);
      records.push({
        plate: plate || "-",
        status,
        time: timeMatch ? timeMatch[0] : "-",
      });
    }
    return { header, records };
  };

  const renderAssistantContent = (content, meta) => {
    if (!content) return null;
    const rows = meta?.rows || [];
    const questionText = meta?.question || "";
    const quickSpec = QUICK_SPECS.get(normalizeQuestion(questionText));

    if (rows.length > 0 && quickSpec) {
      const resolvedRows = rows.map((row) => {
        const resolved = {};
        quickSpec.columns.forEach((col) => {
          if (col.numeric) {
            if (row[col.key] !== undefined) {
              resolved[col.label] = row[col.key];
            } else {
              const numericValue = Object.values(row).find((value) => typeof value === "number");
              resolved[col.label] = numericValue ?? "-";
            }
          } else if (row[col.key] !== undefined) {
            const value = row[col.key];
            if (col.key === "plate_number") {
              resolved[col.label] = formatPlateDisplay(value);
            } else {
              resolved[col.label] = col.format ? col.format(value) : value;
            }
          } else {
            resolved[col.label] = "-";
          }
        });
        return resolved;
      });

      return (
        <div className="parking-chat-answer">
          <div className="parking-chat-table">
            <div
              className="parking-chat-table-header"
              style={{ gridTemplateColumns: `repeat(${quickSpec.columns.length}, minmax(120px, 1fr))` }}
            >
              {quickSpec.columns.map((col) => (
                <span key={col.label}>{col.label}</span>
              ))}
            </div>
            {resolvedRows.map((record, idx) => (
              <div
                key={`${idx}-${record[quickSpec.columns[0].label]}`}
                className="parking-chat-table-row"
                style={{ gridTemplateColumns: `repeat(${quickSpec.columns.length}, minmax(120px, 1fr))` }}
              >
                {quickSpec.columns.map((col) => {
                  const value = record[col.label] ?? "-";
                  if (col.badge) {
                    const statusValue = String(value || "").toLowerCase();
                    return (
                      <span key={col.label} className={`badge status-${statusValue}`}>
                        {value}
                      </span>
                    );
                  }
                  return <span key={col.label}>{value}</span>;
                })}
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (rows.length > 0 && !quickSpec) {
      return (
        <div className="parking-chat-answer">
          <div className="parking-chat-answer-lines">
            {rows.map((row, idx) => {
              const values = LINE_KEYS.map((key) => {
                const value = row[key];
                if (key === "plate_number") return formatPlateDisplay(value);
                return value;
              }).filter((value) => value !== undefined && value !== null);
              const line = values.length > 0 ? values.join(" | ") : JSON.stringify(row);
              return (
                <div key={`${idx}-${line}`} className="parking-chat-answer-item">
                  {line}
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    const { header, records } = parseAssistantRecords(content);
    if (records.length >= 2) {
      return (
        <div className="parking-chat-answer">
          {header && <p className="parking-chat-answer-header">{header}</p>}
          <div className="parking-chat-table">
            <div className="parking-chat-table-header">
              <span>Plate</span>
              <span>Status</span>
              <span>Time</span>
            </div>
            {records.map((record, idx) => (
              <div key={`${record.plate}-${idx}`} className="parking-chat-table-row">
                <span>{formatPlateDisplay(record.plate)}</span>
                <span className={`badge status-${record.status.toLowerCase()}`}>{record.status}</span>
                <span>{record.time}</span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    const parts = content.split(" - ").map((item) => item.trim()).filter(Boolean);
    if (parts.length <= 1) {
      return <p>{content}</p>;
    }
    let inlineHeader = "";
    if (parts[0].includes(":") && parts[0].length < 120) {
      inlineHeader = parts.shift();
    }
    return (
      <div className="parking-chat-answer">
        {inlineHeader && <p className="parking-chat-answer-header">{inlineHeader}</p>}
        <div className="parking-chat-answer-lines">
          {parts.map((line, idx) => (
            <div key={`${line}-${idx}`} className="parking-chat-answer-item">
              {line}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const submitQuestion = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || chatLoading) return;
    setChatLoading(true);
    setChat((prev) => [...prev, { role: "user", content: trimmed }]);
    setQuestion("");
    try {
      const res = await fetch(`${API_PREFIX}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Query failed.");
      }
      setChat((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer || "No answer generated.",
          meta: { question: trimmed, rows: Array.isArray(data.rows) ? data.rows : [] },
        },
      ]);
    } catch (err) {
      setChat((prev) => [...prev, { role: "assistant", content: err.message || "Query failed." }]);
    } finally {
      setChatLoading(false);
    }
  };

  const sendQuestion = async (event) => {
    event.preventDefault();
    await submitQuestion(question);
  };

  return (
    <div className="app parking-app">
      <header className="hero parking-hero">
        <div className="hero-content">
          <span className="badge">Smart Parking</span>
          <h1>Smart Parking Access Control</h1>
          <p>Simulation de portail avec verification base, alertes et analytics RAG.</p>
        </div>
      </header>

      <main className="parking-grid">
        <section className="panel parking-section detection">
          <div className="panel-header">
            <h2>Detection Camera</h2>
            <p>Upload d&apos;image ou video vehicule pour detection plaque et decision portail.</p>
          </div>

          <form onSubmit={submit}>
            <div className="mlpdr-mode-grid">
              {Object.entries(OCR_MODES).map(([value, label]) => (
                <label key={value} className={`mlpdr-mode-card ${ocrMode === value ? "active" : ""}`}>
                  <input
                    type="radio"
                    name="ocr_mode"
                    value={value}
                    checked={ocrMode === value}
                    onChange={(event) => setOcrMode(event.target.value)}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>

            <label className="file-input file-input-drop">
              <input
                type="file"
                accept="image/*,video/*"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
              <span>{file ? file.name : "Drop image or video here or click to browse"}</span>
            </label>

            <button className="btn primary" type="submit" disabled={loading}>
              {loading ? "Processing..." : "Detect & Decide"}
            </button>
          </form>

          {error && <p className="state error">Error: {error}</p>}

          {previewUrl && (
            <div className="mlpdr-preview-box">
              <p className="state">Input preview</p>
              {isVideoFile(file) ? (
                <video src={previewUrl} controls />
              ) : (
                <img src={previewUrl} alt="Selected vehicle" />
              )}
            </div>
          )}

          {result?.artifacts?.input && isVideoFile(file) && (
            <div className="mlpdr-preview-box">
              <p className="state">Best detection frame</p>
              <img src={result.artifacts.input} alt="Best detection frame" />
            </div>
          )}
        </section>

        <section className="panel parking-section gate">
          <div className="panel-header">
            <h2>Gate Status</h2>
            <p>Simulation du portail en temps reel.</p>
          </div>
          <div className={`parking-gate ${gateState === "OPEN" ? "open" : "closed"}`}>
            <div className="parking-gate-arm" />
            <div className="parking-gate-post" />
          </div>
          <div className="parking-gate-meta">
            <strong>{gateLabel}</strong>
            <span>{result?.decision?.action || "Awaiting detection"}</span>
          </div>
        </section>

        <section className="panel parking-section live">
          <div className="panel-header">
            <h2>Live Detection</h2>
            <p>Derniere detection plaque et decision.</p>
          </div>
          {!result && <p className="state">No detection yet.</p>}
          {result && (
            <div className="parking-live">
              <div>
                <span className="state">Plate detected</span>
                <p className="parking-plate">{formatPlateDisplay(result.plate_text || "-")}</p>
              </div>
              <div className="parking-live-grid">
                <div>
                  <span className="state">Owner</span>
                  <strong>{result.decision.owner_name || "Unknown"}</strong>
                </div>
                <div>
                  <span className="state">Status</span>
                  <strong>{result.decision.status}</strong>
                </div>
                <div>
                  <span className="state">Event</span>
                  <strong>{result.decision.event}</strong>
                </div>
                <div>
                  <span className="state">Department</span>
                  <strong>{result.decision.vehicle_type || "N/A"}</strong>
                </div>
                <div>
                  <span className="state">Timestamp</span>
                  <strong>{formatTimestamp(result.timestamp)}</strong>
                </div>
                <div>
                  <span className="state">Action</span>
                  <strong>{result.decision.action}</strong>
                </div>
              </div>
            </div>
          )}
        </section>

        <section className="panel parking-section stats">
          <div className="panel-header">
            <h2>Statistics</h2>
            <p>Resume journalier et occupation actuelle.</p>
          </div>
          {!stats && <p className="state">Loading stats...</p>}
          {stats && (
            <div className="parking-stats">
              <div>
                <span>Total vehicles</span>
                <strong>{stats.total_vehicles}</strong>
              </div>
              <div>
                <span>Authorized</span>
                <strong>{stats.authorized}</strong>
              </div>
              <div>
                <span>Blacklisted</span>
                <strong>{stats.blacklisted}</strong>
              </div>
              <div>
                <span>Entries today</span>
                <strong>{stats.entries_today}</strong>
              </div>
              <div>
                <span>Unknown today</span>
                <strong>{stats.unknown_today}</strong>
              </div>
              <div>
                <span>Avg duration (min)</span>
                <strong>{Math.round(stats.average_parking_minutes_today || 0)}</strong>
              </div>
              <div>
                <span>Currently inside</span>
                <strong>{stats.currently_inside}</strong>
              </div>
            </div>
          )}
        </section>

        <section className="panel parking-section parking-table history">
          <div className="panel-header">
            <h2>Parking History</h2>
            <p>Derniers passages enregistres.</p>
          </div>
          {logs.length === 0 && <p className="state">No logs yet.</p>}
          {logs.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Plate</th>
                  <th>Status</th>
                  <th>Entry</th>
                  <th>Exit</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((item) => (
                  <tr key={item.id}>
                    <td>{formatPlateDisplay(item.plate_number)}</td>
                    <td>{item.status}</td>
                    <td>{formatTimestamp(item.entry_time)}</td>
                    <td>{formatTimestamp(item.exit_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="panel parking-section parking-table alerts">
          <div className="panel-header">
            <h2>Alerts</h2>
            <p>Vehicules blacklistes et detections inconnues.</p>
          </div>
          <div className="parking-alerts">
            <div>
              <h3>Blacklisted</h3>
              {alerts.blacklisted.length === 0 && <p className="state">No alerts.</p>}
              {alerts.blacklisted.map((item) => (
                <div key={`blk-${item.id}`} className="parking-alert-item">
                  <strong>{formatPlateDisplay(item.plate_number)}</strong>
                  <span>{formatTimestamp(item.entry_time)}</span>
                </div>
              ))}
            </div>
            <div>
              <h3>Unknown</h3>
              {alerts.unknown.length === 0 && <p className="state">No unknown plates.</p>}
              {alerts.unknown.map((item) => (
                <div key={`unk-${item.id}`} className="parking-alert-item">
                  <strong>{formatPlateDisplay(item.plate_number)}</strong>
                  <span>{formatTimestamp(item.detected_at)}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="panel parking-section reports">
          <div className="panel-header">
            <h2>Rapports de presence</h2>
            <p>Generer des rapports PDF et suivre la presence par periode.</p>
          </div>
          <div className="reports-grid">
            <div className="reports-card">
              <h3>Generation</h3>
              <div className="reports-form">
                <label>
                  <span>Type de rapport</span>
                  <select
                    value={reportType}
                    onChange={(event) => {
                      setReportType(event.target.value);
                      setReportPreview(null);
                    }}
                  >
                    {REPORT_TYPES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>

                {reportType === "daily" && (
                  <label>
                    <span>Date</span>
                    <input type="date" value={reportDate} onChange={(event) => setReportDate(event.target.value)} />
                  </label>
                )}

                {reportType === "weekly" && (
                  <div className="reports-inline">
                    <label>
                      <span>Annee</span>
                      <input
                        type="number"
                        min="2020"
                        max="2100"
                        value={reportYear}
                        onChange={(event) => setReportYear(event.target.value)}
                      />
                    </label>
                    <label>
                      <span>Semaine</span>
                      <input
                        type="number"
                        min="1"
                        max="53"
                        value={reportWeek}
                        onChange={(event) => setReportWeek(event.target.value)}
                      />
                    </label>
                  </div>
                )}

                {reportType === "monthly" && (
                  <div className="reports-inline">
                    <label>
                      <span>Annee</span>
                      <input
                        type="number"
                        min="2020"
                        max="2100"
                        value={reportYear}
                        onChange={(event) => setReportYear(event.target.value)}
                      />
                    </label>
                    <label>
                      <span>Mois</span>
                      <input
                        type="number"
                        min="1"
                        max="12"
                        value={reportMonth}
                        onChange={(event) => setReportMonth(event.target.value)}
                      />
                    </label>
                  </div>
                )}

                {reportType === "yearly" && (
                  <label>
                    <span>Annee</span>
                    <input
                      type="number"
                      min="2020"
                      max="2100"
                      value={reportYear}
                      onChange={(event) => setReportYear(event.target.value)}
                    />
                  </label>
                )}

                {reportType === "custom" && (
                  <div className="reports-inline">
                    <label>
                      <span>Date debut</span>
                      <input
                        type="date"
                        value={reportStartDate}
                        onChange={(event) => setReportStartDate(event.target.value)}
                      />
                    </label>
                    <label>
                      <span>Date fin</span>
                      <input
                        type="date"
                        value={reportEndDate}
                        onChange={(event) => setReportEndDate(event.target.value)}
                      />
                    </label>
                  </div>
                )}

                <div className="reports-actions">
                  <button type="button" className="btn secondary" onClick={previewReport} disabled={reportLoading}>
                    {reportLoading ? "..." : "Previsualiser"}
                  </button>
                  <button type="button" className="btn primary" onClick={generateReportPdf} disabled={reportLoading}>
                    {reportLoading ? "..." : "Generer PDF"}
                  </button>
                </div>

                {reportError && <p className="state error">Erreur: {reportError}</p>}
              </div>
            </div>

            <div className="reports-card">
              <h3>Previsualisation</h3>
              {!reportPreview && <p className="state">Aucune previsualisation disponible.</p>}
              {reportPreview && (
                <div className="reports-preview">
                  <div className="reports-meta">
                    <span>Type: {reportTypeLabel(reportPreview.report_type)}</span>
                    <span>
                      Periode: {reportPreview.start_date} au {reportPreview.end_date}
                    </span>
                    <span>Genere le: {formatTimestamp(reportPreview.generated_at)}</span>
                  </div>
                  <div className="reports-stats">
                    <div>
                      <span>Total employes</span>
                      <strong>{reportPreview.summary.total_employees}</strong>
                    </div>
                    <div>
                      <span>Presents</span>
                      <strong>{reportPreview.summary.employees_present}</strong>
                    </div>
                    <div>
                      <span>Retards</span>
                      <strong>{reportPreview.summary.total_late}</strong>
                    </div>
                    <div>
                      <span>Anomalies</span>
                      <strong>{reportPreview.summary.total_anomalies}</strong>
                    </div>
                    <div>
                      <span>Temps total</span>
                      <strong>{formatMinutes(reportPreview.summary.total_presence_minutes)}</strong>
                    </div>
                    <div>
                      <span>Temps moyen</span>
                      <strong>{formatMinutes(reportPreview.summary.avg_presence_minutes)}</strong>
                    </div>
                  </div>
                  <div className="reports-table">
                    <div className="reports-table-header">
                      <span>Employe</span>
                      <span>Plaque</span>
                      <span>Jours presents</span>
                      <span>Retards</span>
                      <span>Temps total</span>
                      <span>Statut</span>
                    </div>
                    {(reportPreview.employees || []).slice(0, 8).map((employee) => (
                      <div key={employee.plate_number || employee.full_name} className="reports-table-row">
                        <span>{employee.full_name}</span>
                        <span>{formatPlateDisplay(employee.plate_number)}</span>
                        <span>{employee.days_present}</span>
                        <span>{employee.late_count}</span>
                        <span>{formatMinutes(employee.total_minutes)}</span>
                        <span>{employee.status}</span>
                      </div>
                    ))}
                  </div>
                  {reportPreview.download_url && (
                    <a className="btn secondary" href={reportPreview.download_url} target="_blank" rel="noreferrer">
                      Telecharger PDF
                    </a>
                  )}
                </div>
              )}
            </div>

            <div className="reports-card">
              <h3>Historique</h3>
              {reportHistory.length === 0 && <p className="state">Aucun rapport genere.</p>}
              <div className="reports-history">
                {reportHistory.map((item) => (
                  <div key={item.report_id} className="reports-history-item">
                    <div>
                      <strong>{reportTypeLabel(item.report_type)}</strong>
                      <span>{item.start_date} au {item.end_date}</span>
                      <span>{formatTimestamp(item.generated_at)}</span>
                    </div>
                    <a className="btn secondary" href={item.download_url} target="_blank" rel="noreferrer">
                      Telecharger
                    </a>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="panel parking-section chat">
          <div className="panel-header">
            <h2>Analytics Chat</h2>
            <p>Posez une question en langage naturel sur le parking.</p>
          </div>
          <div className="parking-chat">
            <div className="parking-chat-quick">
              {QUICK_QUESTIONS.map((item) => (
                <button
                  key={item}
                  type="button"
                  className="parking-chat-chip"
                  onClick={() => submitQuestion(item)}
                  disabled={chatLoading}
                >
                  {item}
                </button>
              ))}
            </div>
            <div className="parking-chat-history">
              {chat.length === 0 && <p className="state">No questions yet.</p>}
              {chat.map((item, index) => (
                <div key={`${item.role}-${index}`} className={`parking-chat-bubble ${item.role}`}>
                  <strong>{item.role === "user" ? "You" : "Assistant"}</strong>
                  {item.role === "assistant"
                    ? renderAssistantContent(item.content, item.meta)
                    : <p>{item.content}</p>}
                </div>
              ))}
            </div>
            <form className="parking-chat-form" onSubmit={sendQuestion}>
              <input
                type="text"
                placeholder="Ex: Qui était présent à 08:30 ?"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
              />
              <button type="submit" className="btn secondary">
                {chatLoading ? "..." : "Ask"}
              </button>
            </form>
          </div>
        </section>
      </main>
    </div>
  );
}
