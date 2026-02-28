import { useState } from "react";

export default function UploadForm({ onUpload, loading, error, manualTypeHint }) {
  const [file, setFile] = useState(null);
  const [forcedDocType, setForcedDocType] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file || loading) {
      return;
    }
    await onUpload(file, forcedDocType || null);
  };

  return (
    <form className="panel upload-panel" onSubmit={handleSubmit}>
      <div className="panel-header">
        <h2>Upload OCR Document</h2>
        <p>PDF or image (jpg, jpeg, png).</p>
      </div>

      <label className="file-input">
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
        />
        <span>{file ? file.name : "Choose a file"}</span>
      </label>

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

      <button className="btn primary" type="submit" disabled={!file || loading}>
        {loading ? "Uploading..." : "Upload"}
      </button>

      {manualTypeHint && (
        <p className="state warn">
          Type detection is uncertain. Choose a document type override, then upload again.
        </p>
      )}
      {error && <p className="state error">Error: {error}</p>}
    </form>
  );
}
