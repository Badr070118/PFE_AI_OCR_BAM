import { useEffect, useState } from "react";
import { formatPlateDisplay } from "../utils/plate";

const rawApiBase = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const API_PREFIX = rawApiBase ? `${rawApiBase}/api/mlpdr` : "/api/mlpdr";

const OCR_MODES = {
  trained: "Moroccan Plate (Custom OCR)",
  tesseract: "General Plate (Tesseract-OCR)",
};

export default function MlpdrPage() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [ocrMode, setOcrMode] = useState("trained");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [response, setResponse] = useState(null);

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const normalizeArtifacts = (artifacts = {}) => ({
    input: artifacts.input ? `${API_PREFIX}${artifacts.input}` : "",
    detection: artifacts.detection ? `${API_PREFIX}${artifacts.detection}` : "",
    plate: artifacts.plate ? `${API_PREFIX}${artifacts.plate}` : "",
    segmented: artifacts.segmented ? `${API_PREFIX}${artifacts.segmented}` : "",
  });

  const resetTransientState = () => {
    setError("");
    setResponse(null);
  };

  const handleFile = (nextFile) => {
    resetTransientState();
    setFile(nextFile || null);
  };

  const handleFileChange = (event) => {
    handleFile(event.target.files?.[0] || null);
  };

  const onDrop = (event) => {
    event.preventDefault();
    handleFile(event.dataTransfer.files?.[0] || null);
  };

  const onDragOver = (event) => {
    event.preventDefault();
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!file) {
      setError("Select an image first.");
      return;
    }

    setLoading(true);
    resetTransientState();

    try {
      const body = new FormData();
      body.append("image", file);
      body.append("ocr_mode", ocrMode);

      const res = await fetch(`${API_PREFIX}/upload`, {
        method: "POST",
        body,
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Upload failed.");
      }

      setResponse({
        ...data,
        artifacts: normalizeArtifacts(data.artifacts),
      });
    } catch (err) {
      setError(err.message || "Unexpected error.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-content">
          <span className="badge">MLPDR</span>
          <h1>Moroccan Plate Detection & Recognition</h1>
          <p>
            Meme theme institutionnel que l&apos;accueil. Le contenu et les appels API MLPDR restent identiques.
          </p>
        </div>
      </header>

      <main className="grid">
        <section className="panel">
          <div className="panel-header">
            <h2>Upload Plaque</h2>
            <p>Choisis une image vehicule et un mode OCR avant de lancer la detection.</p>
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
                    onChange={(e) => setOcrMode(e.target.value)}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>

            <label className="file-input file-input-drop" onDrop={onDrop} onDragOver={onDragOver}>
              <input type="file" accept="image/*" onChange={handleFileChange} />
              <span>{file ? file.name : "Drop image here or click to browse"}</span>
            </label>

            <button className="btn primary" type="submit" disabled={loading}>
              {loading ? "Processing..." : "Detect Plate"}
            </button>
          </form>

          {error && <p className="state error">Error: {error}</p>}

          {previewUrl && (
            <div className="mlpdr-preview-box">
              <p className="state">Input preview</p>
              <img src={previewUrl} alt="Selected vehicle" />
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>Result</h2>
            <p>Resultat brut MLPDR, statut de detection et texte plaque reconnu.</p>
          </div>

          {!response && <p className="state">No result yet.</p>}

          {response && (
            <>
              <div className="mlpdr-result-head">
                <div className="mlpdr-stat-card">
                  <p className="state">OCR mode</p>
                  <strong>{response.ocr_mode}</strong>
                </div>
                <div className="mlpdr-stat-card">
                  <p className="state">Plate detected</p>
                  <strong>{response.has_plate ? "Yes" : "No"}</strong>
                </div>
              </div>

              <div className="mlpdr-plate-output">
                <p className="state">Recognized plate</p>
                <p className="mlpdr-plate-text">{formatPlateDisplay(response.plate_text || "-")}</p>
              </div>

              <pre className="result">{JSON.stringify(response, null, 2)}</pre>
            </>
          )}
        </section>

        <section className="panel table-panel">
          <div className="panel-header">
            <h2>Artifacts</h2>
            <p>Images generees par MLPDR (detection, crop plaque, segmentation) si disponibles.</p>
          </div>

          {!response && <p className="state">Lance un test pour afficher les artefacts.</p>}

          {response && (
            <div className="mlpdr-artifacts-grid">
              {["input", "detection", "plate", "segmented"].map((key) => {
                const url = response.artifacts?.[key];
                if (!url) {
                  return (
                    <figure className="mlpdr-figure" key={key}>
                      <figcaption>{key}</figcaption>
                      <div className="mlpdr-figure-empty">Aucun artefact</div>
                    </figure>
                  );
                }
                return (
                  <figure className="mlpdr-figure" key={key}>
                    <figcaption>{key}</figcaption>
                    <a href={url} target="_blank" rel="noreferrer">
                      <img src={url} alt={key} />
                    </a>
                  </figure>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
