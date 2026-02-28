import DOMPurify from "dompurify";
import { useEffect, useMemo, useState } from "react";

const DOC_TYPE_LABELS = {
  invoice: "Invoice",
  bank_statement: "Bank statement",
  payment_receipt: "Payment receipt",
  wire_transfer: "Wire transfer",
  unknown: "Unknown",
};

export default function OcrResult({
  text,
  loading,
  detection,
  tablesHtml,
  structuredPagesHtml,
  structuredHtml,
}) {
  const confidence = Number(detection?.confidence || 0);
  const isWeak = detection?.doc_type === "unknown" || confidence < 0.6;
  const safeTables = Array.isArray(tablesHtml) ? tablesHtml : [];
  const safePages = useMemo(() => {
    const pages = structuredPagesHtml?.pages;
    return Array.isArray(pages) ? pages : [];
  }, [structuredPagesHtml]);
  const hasStructured = safePages.length > 0 || Boolean((structuredHtml || "").trim());
  const [viewMode, setViewMode] = useState(hasStructured ? "structured" : "raw");

  useEffect(() => {
    setViewMode(hasStructured ? "structured" : "raw");
  }, [hasStructured, text]);

  return (
    <section className="panel result-panel">
      <div className="panel-header">
        <h2>OCR Text</h2>
        <p>Raw text extracted from the uploaded file.</p>
      </div>

      {!loading && detection && (
        <div className={`detection-card ${isWeak ? "weak" : ""}`}>
          <p className="state" style={{ marginTop: 0 }}>
            Type detected:{" "}
            <strong>{DOC_TYPE_LABELS[detection.doc_type] || detection.doc_type}</strong>{" "}
            ({Math.round(confidence * 100)}%)
          </p>
          {Array.isArray(detection.reasons) && detection.reasons.length > 0 && (
            <ul className="detection-reasons">
              {detection.reasons.slice(0, 4).map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
          {isWeak && (
            <p className="state warn">
              Low confidence or unknown type. Choose a manual type in upload form.
            </p>
          )}
        </div>
      )}

      {loading && <p className="state">Extracting text...</p>}
      {!loading && !text && (
        <p className="state">Upload a file to see the OCR text.</p>
      )}

      {!loading && (hasStructured || text) && (
        <div className="view-toggle">
          <button
            type="button"
            className={`tab ${viewMode === "structured" ? "active" : ""}`}
            onClick={() => setViewMode("structured")}
            disabled={!hasStructured}
          >
            Vue structuree
          </button>
          <button
            type="button"
            className={`tab ${viewMode === "raw" ? "active" : ""}`}
            onClick={() => setViewMode("raw")}
            disabled={!text}
          >
            Texte brut
          </button>
        </div>
      )}

      {!loading && viewMode === "structured" && hasStructured && (
        <div className="structured-pages">
          {safePages.length > 0 ? (
            safePages.map((page, index) => {
              const pageNumber = Number(page?.page || index + 1);
              const rawHtml = String(page?.html || "");
              const sanitized = DOMPurify.sanitize(rawHtml);
              return (
                <article className="structured-page-card" key={`${pageNumber}-${index}`}>
                  <h3>Page {pageNumber}</h3>
                  <div
                    className="structured-render"
                    dangerouslySetInnerHTML={{ __html: sanitized }}
                  />
                </article>
              );
            })
          ) : (
            <article className="structured-page-card">
              <h3>Document</h3>
              <div
                className="structured-render"
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(String(structuredHtml || "")),
                }}
              />
            </article>
          )}
        </div>
      )}

      {!loading && viewMode === "structured" && !hasStructured && safeTables.length > 0 && (
        <div className="tables-section">
          <h3>Tables (detected)</h3>
          {safeTables.map((table, index) => {
            const page = Number(table?.page || index + 1);
            const rawHtml = String(table?.html || "");
            const sanitized = DOMPurify.sanitize(rawHtml);
            return (
              <article className="table-card" key={`${page}-${index}`}>
                <h4>Table page {page}</h4>
                <div
                  className="table-html"
                  dangerouslySetInnerHTML={{ __html: sanitized }}
                />
              </article>
            );
          })}
        </div>
      )}

      {!loading && viewMode === "raw" && text && <pre className="result">{text}</pre>}
    </section>
  );
}
