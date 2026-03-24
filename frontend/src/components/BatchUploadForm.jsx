import { useState } from "react";

export default function BatchUploadForm({ onUpload, loading, error }) {
  const [files, setFiles] = useState([]);
  const [forcedDocType, setForcedDocType] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!files.length || loading) return;
    await onUpload(files, forcedDocType || null);
  };

  const handleFiles = (event) => {
    const list = Array.from(event.target.files || []);
    setFiles(list);
  };

  const filePreview = files.slice(0, 6).map((file) => file.name).join(", ");
  const remaining = files.length - 6;

  return (
    <form className="panel upload-panel" onSubmit={handleSubmit}>
      <div className="panel-header">
        <h2>Batch OCR</h2>
        <p>Selection multiple fichiers ou dossier complet (PDF, JPG, PNG).</p>
      </div>

      <label className="file-input">
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          multiple
          webkitdirectory=""
          directory=""
          onChange={handleFiles}
        />
        <span>{files.length ? `${files.length} file(s) selected` : "Choose files or folder"}</span>
      </label>

      {files.length > 0 && (
        <p className="state">
          {filePreview}
          {remaining > 0 ? ` (+${remaining} more)` : ""}
        </p>
      )}

      <label className="field">
        <span>Document type override (optional)</span>
        <select
          className="input"
          value={forcedDocType}
          onChange={(event) => setForcedDocType(event.target.value)}
          disabled={loading}
        >
          <option value="">Auto detect</option>
          <option value="invoice">Invoice</option>
          <option value="bank_statement">Bank statement</option>
          <option value="payment_receipt">Payment receipt</option>
          <option value="wire_transfer">Wire transfer</option>
        </select>
      </label>

      <button className="btn primary" type="submit" disabled={!files.length || loading}>
        {loading ? "Processing..." : "Run batch"}
      </button>

      {error && <p className="state error">Error: {error}</p>}
    </form>
  );
}
