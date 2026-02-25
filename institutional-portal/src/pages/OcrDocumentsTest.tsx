import { useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Card from "../components/Card";
import Section from "../components/Section";
import SectionTitle from "../components/SectionTitle";

type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

type OcrDocument = {
  id: number;
  file_name: string;
  data: Record<string, JsonValue>;
  raw_text: string | null;
  llama_output: string | null;
  date_uploaded: string;
};

type LlamaProcessResponse = {
  generated_text: string;
  document_id: number | null;
  structured_data: Record<string, JsonValue> | null;
  warning: string | null;
};

type DocumentAskResponse = {
  answer: string;
  found: boolean;
  fields_used: string[];
  evidence: string[];
  confidence: number;
};

function resolveApiBase(path: "/api/ocr") {
  if (typeof window === "undefined") return path;
  const port = window.location.port;
  const isDevServerPort = port === "5173" || port === "4173" || port === "4174" || port === "5180";
  if (isDevServerPort) {
    return `${window.location.protocol}//${window.location.hostname}${path}`;
  }
  return path;
}

async function extractError(response: Response) {
  const raw = await response.text();
  if (!raw) return `HTTP ${response.status}`;
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown; message?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
    if (typeof parsed.message === "string") return parsed.message;
    return raw;
  } catch {
    return raw;
  }
}

async function requestJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new Error(await extractError(response));
  }
  return (await response.json()) as T;
}

function pretty(value: unknown) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function formatDate(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function OcrDocumentsTest() {
  const fileInputId = useId();
  const questionInputId = useId();
  const instructionInputId = useId();
  const apiBase = resolveApiBase("/api/ocr");

  const [documents, setDocuments] = useState<OcrDocument[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [instruction, setInstruction] = useState("Structure le texte OCR en JSON clair pour la base.");
  const [question, setQuestion] = useState("Resume ce document en 3 points.");
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [isSavingJson, setIsSavingJson] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [llamaResult, setLlamaResult] = useState<LlamaProcessResponse | null>(null);
  const [askResult, setAskResult] = useState<DocumentAskResponse | null>(null);

  const selectedDocument = documents.find((doc) => doc.id === selectedId) ?? null;

  async function loadDocuments(preserveSelection = true) {
    setIsLoadingDocs(true);
    setPageError(null);
    try {
      const rows = await requestJson<OcrDocument[]>(`${apiBase}/documents`);
      setDocuments(rows);
      setSelectedId((current) => {
        if (!rows.length) return null;
        if (preserveSelection && current != null && rows.some((doc) => doc.id === current)) return current;
        return rows[0].id;
      });
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Echec de chargement des documents OCR.");
    } finally {
      setIsLoadingDocs(false);
    }
  }

  useEffect(() => {
    void loadDocuments();
  }, []);

  async function handleUpload() {
    if (!selectedFile) {
      setPageError("Selectionne un fichier PDF/JPG/PNG avant l'upload.");
      return;
    }

    setIsUploading(true);
    setPageError(null);
    setAskResult(null);
    setLlamaResult(null);

    try {
      const form = new FormData();
      form.append("file", selectedFile);

      const created = await requestJson<OcrDocument>(`${apiBase}/upload`, {
        method: "POST",
        body: form,
      });

      await loadDocuments(false);
      setSelectedId(created.id);
      setSelectedFile(null);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Upload OCR impossible.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleProcessWithLlama() {
    if (!selectedDocument?.raw_text?.trim()) {
      setPageError("Le document selectionne ne contient pas de texte OCR.");
      return;
    }

    setIsProcessing(true);
    setPageError(null);
    setLlamaResult(null);

    try {
      const payload = {
        text: selectedDocument.raw_text,
        instruction: instruction.trim() || undefined,
        document_id: selectedDocument.id,
        sync_data: true,
      };
      const result = await requestJson<LlamaProcessResponse>(`${apiBase}/process_with_llama`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setLlamaResult(result);
      await loadDocuments();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Erreur de structuration Llama.");
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleSaveStructuredJson() {
    if (!selectedDocument) {
      setPageError("Aucun document selectionne.");
      return;
    }
    if (!llamaResult?.structured_data) {
      setPageError("Aucun JSON structure a sauvegarder.");
      return;
    }

    setIsSavingJson(true);
    setPageError(null);
    try {
      await requestJson<OcrDocument>(`${apiBase}/documents/${selectedDocument.id}/data`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: llamaResult.structured_data, merge: true }),
      });
      await loadDocuments();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Echec de sauvegarde JSON.");
    } finally {
      setIsSavingJson(false);
    }
  }

  async function handleAskDocument() {
    if (!selectedDocument) {
      setPageError("Selectionne un document avant de poser une question.");
      return;
    }
    if (!question.trim()) {
      setPageError("Saisis une question.");
      return;
    }

    setIsAsking(true);
    setPageError(null);
    setAskResult(null);
    try {
      const result = await requestJson<DocumentAskResponse>(`${apiBase}/documents/${selectedDocument.id}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      setAskResult(result);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Echec du chat document.");
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <>
      <Section className="pt-8 sm:pt-10">
        <div className="space-y-5">
          <nav aria-label="Breadcrumb" className="text-sm text-muted">
            <ol className="flex flex-wrap items-center gap-2">
              <li>
                <Link to="/" className="hover:text-primary">
                  Accueil
                </Link>
              </li>
              <li aria-hidden>/</li>
              <li>
                <Link to="/tests" className="hover:text-primary">
                  Tests
                </Link>
              </li>
              <li aria-hidden>/</li>
              <li className="font-medium text-ink">OCR Documents</li>
            </ol>
          </nav>

          <div className="hero-panel institution-card rounded-2xl border border-border p-6 sm:p-8">
            <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
              <div>
                <Badge tone="accent">Test reel OCR</Badge>
                <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">
                  OCR Documents, structuration Llama et chat
                </h1>
                <p className="mt-4 max-w-3xl text-base leading-7 text-muted">
                  Page de test unifiee pour le module OCR documents. Upload un fichier, consulte la base, lance la
                  structuration Llama 3.1 8B et interroge le document depuis la meme interface thematisee.
                </p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button onClick={() => void loadDocuments()} variant="secondary">
                    {isLoadingDocs ? "Chargement..." : "Rafraichir documents"}
                  </Button>
                  <Button href="http://localhost/ocr" target="_blank" rel="noreferrer">
                    Ouvrir interface OCR existante
                  </Button>
                </div>
              </div>

              <Card className="bg-white/80">
                <p className="text-xs uppercase tracking-[0.08em] text-primary">Configuration API</p>
                <div className="mt-3 space-y-3 text-sm">
                  <div className="rounded-lg border border-border bg-surface p-3">
                    <div className="text-xs uppercase tracking-[0.07em] text-muted">Base OCR</div>
                    <code className="mt-1 block break-all text-primary">{apiBase}</code>
                  </div>
                  <div className="rounded-lg border border-border bg-surface p-3">
                    <div className="text-xs uppercase tracking-[0.07em] text-muted">Sante</div>
                    <code className="mt-1 block break-all text-primary">http://localhost/health/ocr</code>
                  </div>
                  <div className="rounded-lg border border-border bg-surface p-3 text-muted">
                    Si tu lances ce front avec Vite (:5173), la page appelle automatiquement les APIs via
                    http://localhost/...
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </Section>

      <Section tone="soft">
        <SectionTitle
          eyebrow="Operations"
          title="Upload et gestion des documents"
          subtitle="Charge un fichier OCR, puis selectionne un document pour lancer la structuration et le chat."
        />

        {pageError ? (
          <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {pageError}
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <Card>
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-ink">Upload OCR</h3>
                <p className="mt-1 text-sm text-muted">Formats supportes: PDF, JPG, JPEG, PNG.</p>
              </div>

              <div className="space-y-2">
                <label htmlFor={fileInputId} className="text-sm font-medium text-ink">
                  Fichier document
                </label>
                <input
                  id={fileInputId}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/*"
                  onChange={(event) => {
                    setSelectedFile(event.target.files?.[0] ?? null);
                  }}
                  className="block w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-ink file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-primary-2"
                />
                {selectedFile ? <p className="text-xs text-muted">Selection: {selectedFile.name}</p> : null}
              </div>

              <div className="flex flex-wrap gap-3">
                <Button onClick={() => void handleUpload()} disabled={isUploading || !selectedFile}>
                  {isUploading ? "Upload en cours..." : "Uploader et OCRiser"}
                </Button>
                <Button variant="secondary" onClick={() => void loadDocuments()} disabled={isLoadingDocs}>
                  {isLoadingDocs ? "Chargement..." : "Rafraichir liste"}
                </Button>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-ink">Documents en base</h3>
                <p className="mt-1 text-sm text-muted">Selectionne un document pour afficher le texte OCR et les resultats.</p>
              </div>
              <Badge tone="primary">{documents.length} doc(s)</Badge>
            </div>
            <div className="mt-4 max-h-[22rem] space-y-2 overflow-auto pr-1">
              {documents.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border bg-surfaceSoft px-4 py-6 text-sm text-muted">
                  Aucun document pour le moment.
                </div>
              ) : (
                documents.map((doc) => {
                  const selected = doc.id === selectedId;
                  return (
                    <button
                      key={doc.id}
                      type="button"
                      onClick={() => {
                        setSelectedId(doc.id);
                        setAskResult(null);
                        setLlamaResult(null);
                      }}
                      className={[
                        "w-full rounded-xl border px-4 py-3 text-left transition",
                        selected ? "border-primary bg-primary/5" : "border-border bg-surface hover:border-primary/20",
                      ].join(" ")}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="truncate text-sm font-semibold text-ink">{doc.file_name}</p>
                        <span className="shrink-0 text-xs text-muted">#{doc.id}</span>
                      </div>
                      <div className="mt-1 text-xs text-muted">{formatDate(doc.date_uploaded)}</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {doc.raw_text ? <Badge tone="muted">OCR texte</Badge> : null}
                        {doc.llama_output ? <Badge tone="accent">Llama</Badge> : null}
                        {Object.keys(doc.data ?? {}).length > 0 ? <Badge tone="primary">JSON</Badge> : null}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </Card>
        </div>
      </Section>

      <Section>
        <SectionTitle
          eyebrow="Workspace"
          title="Document selectionne"
          subtitle="Traitement Llama, sauvegarde du JSON et chat document sur le document actif."
        />

        {!selectedDocument ? (
          <Card>
            <p className="text-sm text-muted">Selectionne un document depuis la liste pour afficher les details.</p>
          </Card>
        ) : (
          <div className="space-y-6">
            <Card>
              <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
                <div>
                  <h3 className="text-lg font-semibold text-ink">{selectedDocument.file_name}</h3>
                  <p className="mt-2 text-sm text-muted">
                    Document #{selectedDocument.id} - charge le {formatDate(selectedDocument.date_uploaded)}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Badge tone="primary">OCR</Badge>
                    <Badge tone="accent">Llama 3.1 8B</Badge>
                    <Badge tone="muted">Chat document</Badge>
                  </div>
                </div>

                <div className="space-y-3 rounded-xl border border-border bg-surfaceSoft p-4">
                  <label htmlFor={instructionInputId} className="text-sm font-medium text-ink">
                    Instruction Llama (structuration)
                  </label>
                  <textarea
                    id={instructionInputId}
                    value={instruction}
                    onChange={(event) => setInstruction(event.target.value)}
                    rows={4}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-ink"
                  />
                  <div className="flex flex-wrap gap-2">
                    <Button onClick={() => void handleProcessWithLlama()} disabled={isProcessing || !selectedDocument.raw_text}>
                      {isProcessing ? "Structuration..." : "Structurer avec Llama"}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => void handleSaveStructuredJson()}
                      disabled={isSavingJson || !llamaResult?.structured_data}
                    >
                      {isSavingJson ? "Sauvegarde..." : "Sauvegarder JSON en base"}
                    </Button>
                  </div>
                  {llamaResult?.warning ? (
                    <p className="text-xs text-amber-700">Warning backend: {llamaResult.warning}</p>
                  ) : null}
                </div>
              </div>
            </Card>

            <div className="grid gap-6 xl:grid-cols-3">
              <Card className="xl:col-span-1">
                <h3 className="text-base font-semibold text-ink">OCR text</h3>
                <p className="mt-1 text-sm text-muted">Texte brut extrait du document.</p>
                <pre className="mt-4 max-h-[28rem] overflow-auto rounded-xl border border-border bg-[#0b1020] p-4 text-xs leading-6 text-slate-100">
                  {selectedDocument.raw_text?.trim() || "Aucun texte OCR disponible."}
                </pre>
              </Card>

              <Card className="xl:col-span-1">
                <h3 className="text-base font-semibold text-ink">Llama output</h3>
                <p className="mt-1 text-sm text-muted">Sortie de structuration (JSON/texte) du backend OCR.</p>
                <pre className="mt-4 max-h-[28rem] overflow-auto rounded-xl border border-border bg-[#0b1020] p-4 text-xs leading-6 text-slate-100">
                  {llamaResult?.generated_text || selectedDocument.llama_output || "No Llama output yet for this document."}
                </pre>
              </Card>

              <Card className="xl:col-span-1">
                <h3 className="text-base font-semibold text-ink">Extracted JSON</h3>
                <p className="mt-1 text-sm text-muted">Donnees structurees stockees/retournees par le backend.</p>
                <pre className="mt-4 max-h-[28rem] overflow-auto rounded-xl border border-border bg-[#0b1020] p-4 text-xs leading-6 text-slate-100">
                  {pretty(llamaResult?.structured_data ?? selectedDocument.data) || "{}"}
                </pre>
              </Card>
            </div>

            <Card>
              <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
                <div className="space-y-2">
                  <label htmlFor={questionInputId} className="text-sm font-medium text-ink">
                    Chat sur le document
                  </label>
                  <textarea
                    id={questionInputId}
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    rows={3}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-ink"
                    placeholder="Pose une question sur le document..."
                  />
                </div>
                <div className="flex gap-2 lg:pb-0.5">
                  <Button onClick={() => void handleAskDocument()} disabled={isAsking || !selectedDocument}>
                    {isAsking ? "Question..." : "Poser la question"}
                  </Button>
                </div>
              </div>

              <div className="mt-5 rounded-xl border border-border bg-surfaceSoft p-4">
                {askResult ? (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={askResult.found ? "primary" : "muted"}>{askResult.found ? "Trouve" : "Partiel"}</Badge>
                      <Badge tone="accent">Confiance {Math.round(askResult.confidence * 100)}%</Badge>
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-ink">Reponse</h4>
                      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted">{askResult.answer}</p>
                    </div>
                    {askResult.fields_used.length ? (
                      <div>
                        <h4 className="text-sm font-semibold text-ink">Champs utilises</h4>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {askResult.fields_used.map((field) => (
                            <Badge key={field} tone="muted">
                              {field}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ) : null}
                    {askResult.evidence.length ? (
                      <div>
                        <h4 className="text-sm font-semibold text-ink">Evidence</h4>
                        <ul className="mt-2 space-y-2">
                          {askResult.evidence.map((evidence) => (
                            <li key={evidence} className="rounded-lg border border-border bg-white px-3 py-2 text-sm text-muted">
                              {evidence}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <p className="text-sm text-muted">Aucune reponse pour le moment. Pose une question sur le document selectionne.</p>
                )}
              </div>
            </Card>
          </div>
        )}
      </Section>
    </>
  );
}
