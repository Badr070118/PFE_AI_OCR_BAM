import { useId, useState } from "react";
import { Link } from "react-router-dom";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Card from "../components/Card";
import Section from "../components/Section";
import SectionTitle from "../components/SectionTitle";

type MlpdrArtifacts = {
  input: string | null;
  detection: string | null;
  plate: string | null;
  segmented: string | null;
};

type MlpdrResponse = {
  result: string;
  plate_text: string;
  has_plate: boolean;
  ocr_mode: "trained" | "tesseract";
  artifacts: MlpdrArtifacts;
};

function resolveApiBase(path: "/api/mlpdr") {
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
  if (!response.ok) throw new Error(await extractError(response));
  return (await response.json()) as T;
}

function pretty(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function normalizeArtifactUrl(path: string | null, apiBase: string) {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (path.startsWith("/api/mlpdr/")) return path;
  if (path.startsWith("/artifacts/") || path.startsWith("/received/")) return `${apiBase}${path}`;
  if (path.startsWith("/")) return path;
  return `${apiBase}/${path}`;
}

const ARABIC_REGEX = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
const ARABIC_TOKEN_REGEX = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+/;
const LRI = "\u2066";
const RLI = "\u2067";
const PDI = "\u2069";

const isolate = (text: string, dir: "ltr" | "rtl") => {
  if (!text) return "";
  return `${dir === "rtl" ? RLI : LRI}${text}${PDI}`;
};

function formatPlateDisplay(value: string | null | undefined) {
  if (!value) return value ?? "";
  const raw = String(value).trim();
  if (!raw) return raw;

  const tokens = raw
    .split(/[-|\s]+/)
    .map((part) => part.trim())
    .filter(Boolean);

  let arabicToken = tokens.find((part) => ARABIC_REGEX.test(part));
  if (!arabicToken) {
    arabicToken = tokens.find((part) => !/^\d+$/.test(part));
  }
  if (!arabicToken) {
    arabicToken = raw.match(ARABIC_TOKEN_REGEX)?.[0] ?? raw.match(/[^\d\s\-|]+/)?.[0] ?? "";
  }
  if (!arabicToken) return raw;

  const remaining = [...tokens];
  const index = remaining.findIndex((part) => part === arabicToken);
  if (index >= 0) remaining.splice(index, 1);

  let numeric = remaining.filter((part) => /^\d+$/.test(part));
  if (numeric.length < 2) {
    const extracted = raw.match(/\d+/g) || [];
    if (extracted.length >= 1) numeric = extracted;
  }

  let left = "";
  let right = "";
  if (numeric.length >= 2) {
    left = numeric[0];
    right = numeric[numeric.length - 1] || "";
    if (right === left && numeric.length > 1) right = numeric[1] || "";
  } else if (numeric.length === 1) {
    left = numeric[0];
    right = remaining.find((part) => part !== left) || "";
  } else {
    left = remaining[0] || "";
    right = remaining.slice(1).join("");
  }

  if (left && right) return `${isolate(left, "ltr")} - ${isolate(arabicToken, "rtl")} - ${isolate(right, "ltr")}`;
  if (left) return `${isolate(left, "ltr")} - ${isolate(arabicToken, "rtl")}`;
  if (right) return `${isolate(arabicToken, "rtl")} - ${isolate(right, "ltr")}`;
  return raw;
}

export default function MlpdrTest() {
  const fileInputId = useId();
  const apiBase = resolveApiBase("/api/mlpdr");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [ocrMode, setOcrMode] = useState<"trained" | "tesseract">("trained");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MlpdrResponse | null>(null);

  async function handleSubmit() {
    if (!selectedFile) {
      setError("Selectionne une image avant de lancer le test MLPDR.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const form = new FormData();
      form.append("image", selectedFile);
      form.append("ocr_mode", ocrMode);

      const response = await requestJson<MlpdrResponse>(`${apiBase}/upload`, {
        method: "POST",
        body: form,
      });

      setResult(response);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Echec du traitement MLPDR.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const artifactEntries = result
    ? (Object.entries(result.artifacts) as Array<[keyof MlpdrArtifacts, string | null]>).map(([label, value]) => [
        label,
        normalizeArtifactUrl(value, apiBase),
      ])
    : [];

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
              <li className="font-medium text-ink">MLPDR Plaques</li>
            </ol>
          </nav>

          <div className="hero-panel institution-card rounded-2xl border border-border p-6 sm:p-8">
            <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
              <div>
                <Badge tone="accent">Test reel MLPDR</Badge>
                <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">
                  Detection et lecture de plaques (MLPDR)
                </h1>
                <p className="mt-4 max-w-3xl text-base leading-7 text-muted">
                  Interface de test thematisee pour le nouveau projet plaques MLPDR. Uploade une image vehicule, choisis
                  le mode OCR et visualise les artefacts de detection et segmentation.
                </p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button onClick={() => void handleSubmit()} disabled={isSubmitting || !selectedFile}>
                    {isSubmitting ? "Traitement..." : "Tester MLPDR"}
                  </Button>
                  <Button href="http://localhost/mlpdr" target="_blank" rel="noreferrer" variant="secondary">
                    Ouvrir interface MLPDR existante
                  </Button>
                </div>
              </div>

              <Card className="bg-white/80">
                <p className="text-xs uppercase tracking-[0.08em] text-primary">Configuration</p>
                <div className="mt-3 space-y-3 text-sm">
                  <div className="rounded-lg border border-border bg-surface p-3">
                    <div className="text-xs uppercase tracking-[0.07em] text-muted">Base MLPDR</div>
                    <code className="mt-1 block break-all text-primary">{apiBase}</code>
                  </div>
                  <div className="rounded-lg border border-border bg-surface p-3">
                    <div className="text-xs uppercase tracking-[0.07em] text-muted">Upload endpoint</div>
                    <code className="mt-1 block break-all text-primary">{apiBase}/upload</code>
                  </div>
                  <div className="rounded-lg border border-border bg-surface p-3 text-muted">
                    Les artefacts retournes par l&apos;API sont automatiquement remappes vers {apiBase}/artifacts et
                    {apiBase}/received.
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </Section>

      <Section tone="soft">
        <SectionTitle
          eyebrow="Upload"
          title="Lancer un test de lecture de plaque"
          subtitle="Charge une image vehicule, choisis un mode OCR et consulte le resultat de lecture ainsi que les artefacts."
        />

        {error ? (
          <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <Card>
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-ink">Image vehicule</h3>
                <p className="mt-1 text-sm text-muted">Formats images (JPG/PNG) recommandes pour la detection.</p>
              </div>

              <div className="space-y-2">
                <label htmlFor={fileInputId} className="text-sm font-medium text-ink">
                  Fichier image
                </label>
                <input
                  id={fileInputId}
                  type="file"
                  accept="image/*,.jpg,.jpeg,.png"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                  className="block w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-ink file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-primary-2"
                />
                {selectedFile ? <p className="text-xs text-muted">Selection: {selectedFile.name}</p> : null}
              </div>

              <fieldset className="space-y-2">
                <legend className="text-sm font-medium text-ink">Mode OCR</legend>
                <div className="grid gap-2 sm:grid-cols-2">
                  {([
                    {
                      value: "trained" as const,
                      label: "trained",
                      description: "Pipeline OCR du modele MLPDR (YOLO OCR).",
                    },
                    {
                      value: "tesseract" as const,
                      label: "tesseract",
                      description: "Fallback OCR Tesseract sur la plaque detectee.",
                    },
                  ]).map((option) => (
                    <label
                      key={option.value}
                      className={[
                        "cursor-pointer rounded-xl border p-3 transition",
                        ocrMode === option.value ? "border-primary bg-primary/5" : "border-border bg-surface hover:border-primary/20",
                      ].join(" ")}
                    >
                      <div className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="ocr-mode"
                          value={option.value}
                          checked={ocrMode === option.value}
                          onChange={() => setOcrMode(option.value)}
                          className="h-4 w-4 accent-primary"
                        />
                        <span className="text-sm font-semibold text-ink">{option.label}</span>
                      </div>
                      <p className="mt-2 text-xs leading-5 text-muted">{option.description}</p>
                    </label>
                  ))}
                </div>
              </fieldset>

              <div className="flex flex-wrap gap-3">
                <Button onClick={() => void handleSubmit()} disabled={isSubmitting || !selectedFile}>
                  {isSubmitting ? "Traitement en cours..." : "Lancer la detection"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setResult(null);
                    setError(null);
                  }}
                >
                  Reinitialiser resultat
                </Button>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-ink">Resultat MLPDR</h3>
                <p className="mt-1 text-sm text-muted">Lecture plaque, presence detectee et informations de traitement.</p>
              </div>
              {result ? (
                <Badge tone={result.has_plate ? "primary" : "muted"}>{result.has_plate ? "Plaque detectee" : "Aucune plaque"}</Badge>
              ) : (
                <Badge tone="muted">En attente</Badge>
              )}
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-border bg-surfaceSoft p-4">
                <div className="text-xs uppercase tracking-[0.08em] text-muted">Plate text</div>
                <div className="mt-2 text-xl font-semibold text-primary">
                  {formatPlateDisplay(result?.plate_text || "-")}
                </div>
              </div>
              <div className="rounded-xl border border-border bg-surfaceSoft p-4">
                <div className="text-xs uppercase tracking-[0.08em] text-muted">Mode OCR</div>
                <div className="mt-2 text-xl font-semibold text-ink">{result?.ocr_mode || ocrMode}</div>
              </div>
            </div>

            <pre className="mt-4 max-h-72 overflow-auto rounded-xl border border-border bg-[#0b1020] p-4 text-xs leading-6 text-slate-100">
              {result ? pretty(result) : "Aucun resultat pour le moment."}
            </pre>
          </Card>
        </div>
      </Section>

      <Section>
        <SectionTitle
          eyebrow="Artifacts"
          title="Artefacts de traitement"
          subtitle="Apercus des images retournees par MLPDR (image source, detection, plaque, segmentation si disponible)."
        />

        {!result ? (
          <Card>
            <p className="text-sm text-muted">Lance un test MLPDR pour afficher les artefacts.</p>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {artifactEntries.map(([label, url]) => (
              <Card key={label} className="overflow-hidden p-0">
                <div className="border-b border-border px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold text-ink">{label}</h3>
                    {url ? <Badge tone="primary">OK</Badge> : <Badge tone="muted">N/A</Badge>}
                  </div>
                </div>

                {url ? (
                  <div className="p-4">
                    <a href={url} target="_blank" rel="noreferrer" className="group block">
                      <img
                        src={url}
                        alt={`Artefact ${label}`}
                        className="h-44 w-full rounded-lg border border-border bg-surfaceSoft object-cover"
                        loading="lazy"
                      />
                      <div className="mt-3 break-all text-xs text-primary group-hover:underline">{url}</div>
                    </a>
                  </div>
                ) : (
                  <div className="px-4 py-8 text-sm text-muted">Aucun artefact pour ce champ.</div>
                )}
              </Card>
            ))}
          </div>
        )}
      </Section>
    </>
  );
}
