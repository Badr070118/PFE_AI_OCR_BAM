import { useEffect, useState } from "react";
import UploadForm from "../components/UploadForm";
import BatchUploadForm from "../components/BatchUploadForm";
import DocumentsList from "../components/DocumentsList";
import OcrResult from "../components/OcrResult";
import { fetchBatchDetail, fetchBatchHistory, uploadBatch, uploadDocument } from "../services/api";
import ReviewPage from "../review/ReviewPage";
import { navigateTo, useAppRoute } from "../review/routing";

export default function OcrPage() {
  const route = useAppRoute();
  const reviewEnabled = import.meta.env.VITE_REVIEW_FEATURE_ENABLED !== "0";
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [manualTypeHint, setManualTypeHint] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [batchResult, setBatchResult] = useState(null);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchError, setBatchError] = useState("");
  const [batchHistory, setBatchHistory] = useState([]);
  const [batchDetail, setBatchDetail] = useState(null);

  const activeBatch = batchResult || batchDetail;

  const handleUpload = async (file, forcedDocType = null) => {
    // Upload -> show latest result -> refresh documents list.
    setUploadLoading(true);
    setUploadError("");
    setUploadResult(null);
    setManualTypeHint(false);

    try {
      const data = await uploadDocument(file, { forcedDocType: forcedDocType || "" });
      setUploadResult(data);
      const detection = data?.doc_type_detection || null;
      const confidence = Number(detection?.confidence || 0);
      const isWeak = detection?.doc_type === "unknown" || confidence < 0.6;
      setManualTypeHint(isWeak && !forcedDocType);
      setRefreshKey((prev) => prev + 1);
    } catch (err) {
      setUploadError(err?.response?.data?.detail || err.message || "Upload failed");
    } finally {
      setUploadLoading(false);
    }
  };

  const loadBatchHistory = async (fetchDetail = false) => {
    try {
      const items = await fetchBatchHistory(8);
      setBatchHistory(items);
      if (fetchDetail && items.length > 0) {
        const detail = await fetchBatchDetail(items[0].batch_id);
        setBatchDetail(detail);
      }
    } catch (err) {
      // Keep silent: batch is optional UI.
    }
  };

  useEffect(() => {
    loadBatchHistory(true);
  }, []);

  const handleBatchUpload = async (files, forcedDocType = null) => {
    setBatchLoading(true);
    setBatchError("");
    setBatchResult(null);
    try {
      const data = await uploadBatch(files, { forcedDocType: forcedDocType || "" });
      setBatchResult(data);
      setBatchDetail(data);
      setRefreshKey((prev) => prev + 1);
      await loadBatchHistory(false);
    } catch (err) {
      setBatchError(err?.response?.data?.detail || err.message || "Batch upload failed");
    } finally {
      setBatchLoading(false);
    }
  };

  const viewBatchDetail = async (batchId) => {
    try {
      const detail = await fetchBatchDetail(batchId);
      setBatchDetail(detail);
    } catch (err) {
      setBatchError(err?.response?.data?.detail || err.message || "Unable to fetch batch detail");
    }
  };

  if (route.type === "review") {
    if (!reviewEnabled) {
      return (
        <div className="app">
          <section className="panel">
            <p className="state error">Review feature is disabled.</p>
            <button type="button" className="btn primary" onClick={() => navigateTo("/")}>
              Retour a la liste
            </button>
          </section>
        </div>
      );
    }

    return (
      <div className="app">
        <ReviewPage documentId={route.documentId} onBack={() => navigateTo("/")} />
      </div>
    );
  }

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-content">
          <span className="badge">GLM-OCR</span>
          <h1>Scan, extract, and structure your documents.</h1>
          <p>
            Upload PDFs or images, get structured JSON instantly, and keep a
            searchable archive.
          </p>
        </div>
      </header>

      <main className="grid">
        <UploadForm
          onUpload={handleUpload}
          loading={uploadLoading}
          error={uploadError}
          manualTypeHint={manualTypeHint}
        />

        <BatchUploadForm onUpload={handleBatchUpload} loading={batchLoading} error={batchError} />

        <OcrResult
          text={uploadResult?.raw_text || ""}
          loading={uploadLoading}
          detection={uploadResult?.doc_type_detection || null}
          tablesHtml={uploadResult?.tables_html || []}
          structuredPagesHtml={uploadResult?.structured_pages_html || null}
          structuredHtml={uploadResult?.structured_html || ""}
        />

        <section className="panel">
          <div className="panel-header">
            <h2>Batch Summary</h2>
            <p>Dernier lot traite et statut global.</p>
          </div>

          {!activeBatch && <p className="state">No batch processed yet.</p>}

          {activeBatch && (
            <div className="batch-summary">
              <div>
                <span>Batch ID</span>
                <strong>{activeBatch.batch_id}</strong>
              </div>
              <div>
                <span>Status</span>
                <strong>{activeBatch.status}</strong>
              </div>
              <div>
                <span>Total</span>
                <strong>{activeBatch.total_files}</strong>
              </div>
              <div>
                <span>Success</span>
                <strong>{activeBatch.success_count}</strong>
              </div>
              <div>
                <span>Failed</span>
                <strong>{activeBatch.failed_count}</strong>
              </div>
              <div>
                <span>Started</span>
                <strong>{new Date(activeBatch.created_at).toLocaleString()}</strong>
              </div>
            </div>
          )}

          {activeBatch?.results?.length > 0 && (
            <div className="batch-table">
              <div className="batch-table-header">
                <span>File</span>
                <span>Status</span>
                <span>Type</span>
                <span>DB</span>
              </div>
              {activeBatch.results.map((item, idx) => (
                <div key={`${item.filename}-${idx}`} className="batch-table-row">
                  <span>{item.filename}</span>
                  <span className={`badge status-${String(item.status || "").toLowerCase()}`}>{item.status}</span>
                  <span>{item.document_type || "-"}</span>
                  <span>{item.db_id || item.error || "-"}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>Batch History</h2>
            <p>Historique des lots recents.</p>
          </div>
          {batchHistory.length === 0 && <p className="state">No batch history yet.</p>}
          {batchHistory.length > 0 && (
            <div className="batch-history">
              {batchHistory.map((batch) => (
                <button
                  key={batch.batch_id}
                  type="button"
                  className={`batch-history-item ${activeBatch?.batch_id === batch.batch_id ? "active" : ""}`}
                  onClick={() => viewBatchDetail(batch.batch_id)}
                >
                  <div>
                    <strong>Batch #{batch.batch_id}</strong>
                    <span>{new Date(batch.created_at).toLocaleString()}</span>
                  </div>
                  <div className="batch-history-metrics">
                    <span>Total: {batch.total_files}</span>
                    <span>OK: {batch.success_count}</span>
                    <span>KO: {batch.failed_count}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>

        <DocumentsList
          refreshKey={refreshKey}
          onOpenReview={
            reviewEnabled
              ? (documentId) => navigateTo(`/documents/${documentId}/review`)
              : null
          }
        />
      </main>
    </div>
  );
}
