import { useEffect, useMemo, useState } from "react";
import { formatPlateDisplay } from "../utils/plate";

const TABS = [
  { id: "overview", label: "Vue d’ensemble" },
  { id: "reports", label: "Rapports" },
  { id: "history", label: "Historique" },
  { id: "anomalies", label: "Anomalies" },
];

const REPORT_TYPES = [
  { value: "daily", label: "Quotidien" },
  { value: "weekly", label: "Hebdomadaire" },
  { value: "monthly", label: "Mensuel" },
  { value: "yearly", label: "Annuel" },
];

const ANOMALY_LABELS = {
  entry_without_exit: "Entrée sans sortie",
  incoherent: "Événements incohérents",
  duplicates: "Doublons rapprochés",
  unknown_plates: "Plaques inconnues",
  blacklisted: "Plaques blacklistées",
  orphan_exit: "Sortie sans entrée",
};

const formatTimestamp = (value) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
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

  const [anomalyStart, setAnomalyStart] = useState(todayIso);
  const [anomalyEnd, setAnomalyEnd] = useState(todayIso);
  const [anomalies, setAnomalies] = useState(null);
  const [anomalyLoading, setAnomalyLoading] = useState(false);

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

  const fetchAnomalies = async () => {
    setAnomalyLoading(true);
    try {
      const res = await fetch(
        `${apiPrefix}/presence/anomalies?start_date=${anomalyStart}&end_date=${anomalyEnd}`
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Impossible de charger les anomalies.");
      setAnomalies(data);
    } catch (err) {
      setAnomalies({ error: err.message || "Erreur anomalies." });
    } finally {
      setAnomalyLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab !== "overview") return undefined;
    fetchOverview();
    const interval = window.setInterval(fetchOverview, 10000);
    return () => window.clearInterval(interval);
  }, [activeTab, overviewDate]);

  useEffect(() => {
    if (activeTab === "history") {
      fetchHistory();
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === "anomalies") {
      fetchAnomalies();
    }
  }, [activeTab, anomalyStart, anomalyEnd]);
  return (
    <section className="presence-analysis">
      <header className="presence-analysis-head">
        <div>
          <h2>Analyse de présence</h2>
          <p>Module basé uniquement sur les données réelles (employés + logs ANPR + anomalies).</p>
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
                  <span>Anomalies</span>
                  <strong>{overview.summary?.total_anomalies ?? 0}</strong>
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
                  <div className="presence-table">
                    <div className="presence-table-head">
                      <span>Employé</span>
                      <span>Plaque</span>
                      <span>Entrée</span>
                      <span>Sortie</span>
                      <span>Statut</span>
                    </div>
                    {overview.recent_accesses.map((item) => (
                      <div key={`${item.plate_number}-${item.entry_time}`} className="presence-table-row">
                        <span>{item.employee_name || "-"}</span>
                        <span>{formatPlateDisplay(item.plate_number)}</span>
                        <span>{formatTimestamp(item.entry_time)}</span>
                        <span>{formatTimestamp(item.exit_time)}</span>
                        <span>{item.status}</span>
                      </div>
                    ))}
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
                    <span>Date d?but</span>
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
                    <span>Ann?e</span>
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
                  <span>Ann?e</span>
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
                  {reportLoading ? "..." : "G?n?rer PDF"}
                </button>
                <button type="button" className="btn ghost" onClick={resetReportForm} disabled={reportLoading}>
                  R?initialiser
                </button>
              </div>
              {reportError && <p className="presence-error">Erreur: {reportError}</p>}
              {reportResult?.download_url && (
                <div className="presence-report-ready">
                  <span>PDF pr?t.</span>
                  <a className="btn secondary" href={reportResult.download_url} target="_blank" rel="noreferrer">
                    T?l?charger PDF
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
            {history.map((item) => (
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

      {activeTab === "anomalies" && (
        <div className="presence-panel">
          <div className="presence-card">
            <h3>Filtres</h3>
            <div className="presence-inline">
              <label>
                <span>Date début</span>
                <input type="date" value={anomalyStart} onChange={(event) => setAnomalyStart(event.target.value)} />
              </label>
              <label>
                <span>Date fin</span>
                <input type="date" value={anomalyEnd} onChange={(event) => setAnomalyEnd(event.target.value)} />
              </label>
            </div>
          </div>

          <div className="presence-card presence-anomalies-tab">
            <h3>Anomalies réelles</h3>
            {anomalyLoading && <p className="state">Chargement...</p>}
            {!anomalyLoading && anomalies?.error && <p className="state error">{anomalies.error}</p>}
            {!anomalyLoading && anomalies && !anomalies.error && (
              <>
                <div className="presence-metrics">
                  {Object.entries(anomalies.summary || {}).map(([key, value]) => (
                    <div key={key}>
                      <span>{ANOMALY_LABELS[key] || key}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>

                {anomalies.items?.length === 0 && (
                  <p className="state">Aucune anomalie détectée pour cette période.</p>
                )}
                {anomalies.items?.length > 0 && (
                  <div className="presence-table">
                    <div className="presence-table-head">
                      <span>Type</span>
                      <span>Plaque</span>
                      <span>Horodatage</span>
                      <span>Statut</span>
                    </div>
                    {anomalies.items.slice(0, 20).map((item, index) => (
                      <div key={`${item.type}-${index}`} className="presence-table-row">
                        <span>{ANOMALY_LABELS[item.type] || item.type}</span>
                        <span>{formatPlateDisplay(item.plate_number || "-")}</span>
                        <span>{formatTimestamp(item.timestamp)}</span>
                        <span>{item.status || "-"}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
