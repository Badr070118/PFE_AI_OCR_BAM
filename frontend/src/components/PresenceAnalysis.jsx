import { useEffect, useMemo, useRef, useState } from "react";
import { formatPlateDisplay } from "../utils/plate";

const TABS = [
  { id: "overview", label: "Vue d’ensemble" },
  { id: "reports", label: "Rapports" },
  { id: "history", label: "Historique" },
];

const REPORT_TYPES = [
  { value: "daily", label: "Quotidien" },
  { value: "weekly", label: "Hebdomadaire" },
  { value: "monthly", label: "Mensuel" },
  { value: "yearly", label: "Annuel" },
];

const formatTimestamp = (value) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const normalizePlateQuery = (value) => {
  if (!value) return "";
  return value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u064b-\u065f\u0670\u0640]/g, "")
    .replace(/[\u200c\u200d\u200e\u200f]/g, "")
    .replace(/[\u2066-\u2069]/g, "")
    .replace(/[\s-]+/g, "");
};

const formatTimeValue = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
};

const parseTimeFilter = (value) => {
  const trimmed = value.trim();
  if (!trimmed) return { mode: "none" };
  const exactMatch = trimmed.match(/^([01]?\d|2[0-3]):([0-5]\d)$/);
  if (exactMatch) {
    return { mode: "exact", hour: Number(exactMatch[1]), minute: Number(exactMatch[2]) };
  }
  const hourMatch = trimmed.match(/^([01]?\d|2[0-3])(?::)?$/);
  if (hourMatch) {
    return { mode: "hour", hour: Number(hourMatch[1]) };
  }
  return { mode: "invalid" };
};


const toDateInput = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
};

export default function PresenceAnalysis({ apiPrefix }) {
  const today = useMemo(() => new Date(), []);
  const todayIso = useMemo(() => toDateInput(today), [today]);

  const [activeTab, setActiveTab] = useState("overview");

  const [overviewDate, setOverviewDate] = useState(todayIso);
  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const lastLogSignatureRef = useRef("");

  const [reportType, setReportType] = useState("daily");
  const [reportDate, setReportDate] = useState(todayIso);
  const [reportStartDate, setReportStartDate] = useState(todayIso);
  const [reportEndDate, setReportEndDate] = useState(todayIso);
  const [reportYear, setReportYear] = useState(today.getFullYear());
  const [reportMonth, setReportMonth] = useState(today.getMonth() + 1);
  const [reportResult, setReportResult] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyMode, setHistoryMode] = useState("period");
  const [historyStartDate, setHistoryStartDate] = useState("");
  const [historyEndDate, setHistoryEndDate] = useState("");
  const [historyGeneratedDate, setHistoryGeneratedDate] = useState("");
  const [accessQuery, setAccessQuery] = useState("");
  const [accessTimeMode, setAccessTimeMode] = useState("entry");
  const [accessTimeValue, setAccessTimeValue] = useState("");

  const resetAccessFilters = () => {
    setAccessQuery("");
    setAccessTimeMode("entry");
    setAccessTimeValue("");
  };

  const filteredAccesses = useMemo(() => {
    const items = overview?.recent_accesses || [];
    const needle = accessQuery.trim();
    const timeNeedle = accessTimeValue.trim();
    const timeFilter = parseTimeFilter(timeNeedle);
    if (timeNeedle && timeFilter.mode === "invalid") return [];
    if (!needle && !timeNeedle) return items;
    const lowered = needle.toLowerCase();
    const normalizedNeedle = normalizePlateQuery(needle);

    return items.filter((item) => {
      let matchesSearch = true;
      if (needle) {
        const name = (item.employee_name || "").toLowerCase();
        const plate = item.plate_number || "";
        const normalizedPlate = normalizePlateQuery(plate);
        const displayPlate = formatPlateDisplay(plate);
        const normalizedDisplay = normalizePlateQuery(displayPlate);
        matchesSearch = name.includes(lowered)
          || normalizedPlate === normalizedNeedle
          || normalizedDisplay === normalizedNeedle;
      }

      if (!matchesSearch) return false;
      if (!timeNeedle) return true;

      const sourceTime = accessTimeMode === "exit" ? item.exit_time : item.entry_time;
      if (!sourceTime) return false;
      const date = new Date(sourceTime);
      if (Number.isNaN(date.getTime())) return false;
      const hours = date.getHours();
      const minutes = date.getMinutes();

      if (timeFilter.mode === "exact") {
        return hours === timeFilter.hour && minutes === timeFilter.minute;
      }
      if (timeFilter.mode === "hour") {
        return hours >= timeFilter.hour;
      }
      return false;
    });
  }, [overview, accessQuery, accessTimeMode, accessTimeValue]);

  const filteredHistory = useMemo(() => {
    if (historyMode === "generated") {
      const target = historyGeneratedDate.trim();
      if (!target) return history;
      return history.filter((item) => {
        if (!item.generated_at) return false;
        const generated = new Date(item.generated_at);
        if (Number.isNaN(generated.getTime())) return false;
        return generated.toISOString().slice(0, 10) === target;
      });
    }

    const start = historyStartDate.trim();
    const end = historyEndDate.trim();
    if (!start && !end) return history;

    return history.filter((item) => {
      if (!item.start_date || !item.end_date) return false;
      if (start && item.end_date < start) return false;
      if (end && item.start_date > end) return false;
      return true;
    });
  }, [history, historyMode, historyGeneratedDate, historyStartDate, historyEndDate]);

  const buildReportPayload = () => {
    setReportError("");
    if (reportType === "daily") {
      return reportDate ? { report_type: "daily", date: reportDate } : null;
    }
    if (reportType === "weekly") {
      if (!reportStartDate || !reportEndDate) return null;
      return { report_type: "weekly", start_date: reportStartDate, end_date: reportEndDate };
    }
    if (reportType === "monthly") {
      return { report_type: "monthly", year: Number(reportYear), month: Number(reportMonth) };
    }
    if (reportType === "yearly") {
      return { report_type: "yearly", year: Number(reportYear) };
    }
    return null;
  };

  const fetchOverview = async () => {
    setOverviewLoading(true);
    try {
      const res = await fetch(`${apiPrefix}/presence/overview?date=${overviewDate}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Impossible de charger la vue d’ensemble.");
      setOverview(data);
    } catch (err) {
      setOverview({ error: err.message || "Erreur de chargement." });
    } finally {
      setOverviewLoading(false);
    }
  };

  const fetchLatestLogSignature = async () => {
    try {
      const res = await fetch(`${apiPrefix}/logs?limit=1`);
      const data = await res.json().catch(() => ({}));
      const item = data?.items?.[0];
      if (!item) return "";
      const entry = item.entry_time || "";
      const exit = item.exit_time || "";
      return `${item.id || ""}|${entry}|${exit}`;
    } catch {
      return "";
    }
  };


  const generateReport = async () => {
    const payload = buildReportPayload();
    if (!payload) {
      setReportError("Champs manquants pour la génération.");
      return;
    }
    setReportLoading(true);
    try {
      const res = await fetch(`${apiPrefix}/reports/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Génération impossible.");
      setReportResult(data);
      await fetchHistory();
    } catch (err) {
      setReportError(err.message || "Erreur de génération.");
    } finally {
      setReportLoading(false);
    }
  };

  const resetReportForm = () => {
    setReportType("daily");
    setReportDate(todayIso);
    setReportStartDate(todayIso);
    setReportEndDate(todayIso);
    setReportYear(today.getFullYear());
    setReportMonth(today.getMonth() + 1);
    setReportResult(null);
    setReportError("");
  };

  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${apiPrefix}/reports?limit=20`);
      const data = await res.json().catch(() => []);
      setHistory(Array.isArray(data) ? data : []);
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab !== "overview") return undefined;
    let isActive = true;

    const bootstrap = async () => {
      await fetchOverview();
      const signature = await fetchLatestLogSignature();
      if (isActive && signature) {
        lastLogSignatureRef.current = signature;
      }
    };

    bootstrap();

    if (overviewDate !== todayIso) {
      return () => {
        isActive = false;
      };
    }

    const interval = window.setInterval(async () => {
      const signature = await fetchLatestLogSignature();
      if (!signature) return;
      if (!lastLogSignatureRef.current) {
        lastLogSignatureRef.current = signature;
        return;
      }
      if (signature !== lastLogSignatureRef.current) {
        lastLogSignatureRef.current = signature;
        await fetchOverview();
      }
    }, 8000);

    return () => {
      isActive = false;
      window.clearInterval(interval);
    };
  }, [activeTab, overviewDate, todayIso]);

  useEffect(() => {
    if (activeTab === "history") {
      fetchHistory();
    }
  }, [activeTab]);

  return (
    <section className="presence-analysis">
      <header className="presence-analysis-head">
        <div>
          <h2>Analyse de présence</h2>
          <p>Module basé uniquement sur les données réelles (employés + logs ANPR).</p>
        </div>
        <div className="presence-analysis-meta">
          <span>Sources: employees, parking_logs, unknown_detections</span>
          <span>PDFs cohérents avec les rapports</span>
        </div>
      </header>

      <div className="presence-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`presence-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="presence-panel">
          <div className="presence-overview-controls">
            <label>
              <span>Date</span>
              <input type="date" value={overviewDate} onChange={(event) => setOverviewDate(event.target.value)} />
            </label>
          </div>
          {overviewLoading && <p className="state">Chargement...</p>}
          {!overviewLoading && overview?.error && <p className="state error">{overview.error}</p>}
          {!overviewLoading && overview && !overview.error && (
            <>
              <div className="presence-metrics">
                <div>
                  <span>Présents aujourd’hui</span>
                  <strong>{overview.summary?.employees_present ?? 0}</strong>
                </div>
                <div>
                  <span>Absents aujourd’hui</span>
                  <strong>{overview.summary?.employees_absent ?? 0}</strong>
                </div>
                <div>
                  <span>Retards</span>
                  <strong>{overview.summary?.total_late ?? 0}</strong>
                </div>
                <div>
                  <span>Plaques inconnues</span>
                  <strong>{overview.summary?.unknown_plates ?? 0}</strong>
                </div>
              </div>

              <div className="presence-table-block">
                <h3>Derniers accès</h3>
                {overview.recent_accesses?.length === 0 && (
                  <p className="state">Aucun accès enregistré pour cette date.</p>
                )}
                {overview.recent_accesses?.length > 0 && (
                  <div className="presence-access-filters">
                    <label className="presence-filter">
                      <span>Recherche</span>
                      <input
                        type="text"
                        value={accessQuery}
                        onChange={(event) => setAccessQuery(event.target.value)}
                        placeholder="Ex: Salma ou 15181-د-8"
                      />
                    </label>
                    <div className="presence-time-filter">
                      <label className="presence-filter">
                        <span>Filtrer par</span>
                        <select value={accessTimeMode} onChange={(event) => setAccessTimeMode(event.target.value)}>
                          <option value="entry">Heure d'entrée</option>
                          <option value="exit">Heure de sortie</option>
                        </select>
                      </label>
                      <label className="presence-filter">
                        <span>Heure</span>
                        <input
                          type="text"
                          value={accessTimeValue}
                          onChange={(event) => setAccessTimeValue(event.target.value)}
                          placeholder="Ex: 16 ou 15:45"
                        />
                      </label>
                    </div>
                    <div className="presence-filter-actions">
                      <span className="presence-filter-count">{filteredAccesses.length} accès</span>
                      <button
                        type="button"
                        className="btn ghost presence-reset-btn"
                        onClick={resetAccessFilters}
                        disabled={!accessQuery && !accessTimeValue && accessTimeMode === "entry"}
                      >
                        Réinitialiser
                      </button>
                    </div>
                  </div>
                )}
                {overview.recent_accesses?.length > 0 && filteredAccesses.length === 0 && (
                  <p className="state">Aucun accès ne correspond au filtre.</p>
                )}
                {overview.recent_accesses?.length > 0 && filteredAccesses.length > 0 && (
                  <div className="presence-table-scroll">
                    <div className="presence-table">
                      <div className="presence-table-head">
                        <span>Employé</span>
                        <span>Plaque</span>
                        <span>Entrée</span>
                        <span>Sortie</span>
                        <span>Statut</span>
                      </div>
                      {filteredAccesses.map((item) => (
                        <div key={`${item.plate_number}-${item.entry_time}`} className="presence-table-row">
                          <span>{item.employee_name || "-"}</span>
                          <span>{formatPlateDisplay(item.plate_number)}</span>
                          <span>{formatTimestamp(item.entry_time)}</span>
                          <span>{formatTimestamp(item.exit_time)}</span>
                          <span>{item.status}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {activeTab === "reports" && (
        <div className="presence-panel presence-reports-tab">
          <div className="presence-card">
            <h3>Filtres</h3>
            <div className="presence-fields">
              <label>
                <span>Type de rapport</span>
                <select value={reportType} onChange={(event) => setReportType(event.target.value)}>
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
                <div className="presence-inline">
                  <label>
                    <span>Date début</span>
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

              {reportType === "monthly" && (
                <div className="presence-inline">
                  <label>
                    <span>Année</span>
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
                  <span>Année</span>
                  <input
                    type="number"
                    min="2020"
                    max="2100"
                    value={reportYear}
                    onChange={(event) => setReportYear(event.target.value)}
                  />
                </label>
              )}

              <div className="presence-actions">
                <button type="button" className="btn primary" onClick={generateReport} disabled={reportLoading}>
                  {reportLoading ? "..." : "Générer PDF"}
                </button>
                <button type="button" className="btn ghost" onClick={resetReportForm} disabled={reportLoading}>
                  Réinitialiser
                </button>
              </div>
              {reportError && <p className="presence-error">Erreur: {reportError}</p>}
              {reportResult?.download_url && (
                <div className="presence-report-ready">
                  <span>PDF prêt.</span>
                  <a className="btn secondary" href={reportResult.download_url} target="_blank" rel="noreferrer">
                    Télécharger PDF
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === "history" && (
        <div className="presence-panel">
          <div className="presence-card presence-history">
            <h3>Historique des rapports</h3>
            {historyLoading && <p className="state">Chargement...</p>}
            {!historyLoading && history.length === 0 && <p className="state">Aucun rapport généré.</p>}
            {!historyLoading && history.length > 0 && (
              <div className="presence-history-filters">
                <label className="presence-filter">
                  <span>Filtre date</span>
                  <select value={historyMode} onChange={(event) => setHistoryMode(event.target.value)}>
                    <option value="period">Période du rapport</option>
                    <option value="generated">Date de génération</option>
                  </select>
                </label>
                {historyMode === "generated" ? (
                  <label className="presence-filter">
                    <span>Date</span>
                    <input
                      type="date"
                      value={historyGeneratedDate}
                      onChange={(event) => setHistoryGeneratedDate(event.target.value)}
                    />
                  </label>
                ) : (
                  <>
                    <label className="presence-filter">
                      <span>Date début</span>
                      <input
                        type="date"
                        value={historyStartDate}
                        onChange={(event) => setHistoryStartDate(event.target.value)}
                      />
                    </label>
                    <label className="presence-filter">
                      <span>Date fin</span>
                      <input
                        type="date"
                        value={historyEndDate}
                        onChange={(event) => setHistoryEndDate(event.target.value)}
                      />
                    </label>
                  </>
                )}
                <button
                  type="button"
                  className="btn ghost"
                  onClick={() => {
                    setHistoryStartDate("");
                    setHistoryEndDate("");
                    setHistoryGeneratedDate("");
                  }}
                  disabled={!historyStartDate && !historyEndDate && !historyGeneratedDate}
                >
                  Effacer
                </button>
                <span className="presence-filter-count">{filteredHistory.length} rapports</span>
              </div>
            )}
            {!historyLoading && history.length > 0 && filteredHistory.length === 0 && (
              <p className="state">Aucun rapport ne correspond au filtre.</p>
            )}
            {filteredHistory.map((item) => (
              <div key={item.report_id} className="presence-history-item">
                <div>
                  <strong>{item.report_type}</strong>
                  <span>
                    {item.start_date} au {item.end_date}
                  </span>
                  <span>{formatTimestamp(item.generated_at)}</span>
                </div>
                <a className="btn secondary" href={item.download_url} target="_blank" rel="noreferrer">
                  PDF
                </a>
              </div>
            ))}
          </div>
        </div>
      )}

      
    </section>
  );
}
