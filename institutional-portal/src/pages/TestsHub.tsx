import { Link } from "react-router-dom";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Card from "../components/Card";
import Section from "../components/Section";
import SectionTitle from "../components/SectionTitle";

type TestPageItem = {
  title: string;
  path: string;
  description: string;
  tag: string;
  points: string[];
};

const testPages: TestPageItem[] = [
  {
    title: "OCR Documents",
    path: "/tests/ocr",
    tag: "Module OCR",
    description:
      "Interface de test thematisee pour upload de documents, consultation de la base, structuration Llama et chat sur document.",
    points: ["Upload vers /api/ocr/upload", "Liste via /api/ocr/documents", "Structuration + chat document"],
  },
  {
    title: "MLPDR Plaques",
    path: "/tests/mlpdr",
    tag: "Module plaques",
    description:
      "Page de test MLPDR avec upload image, choix du mode OCR (trained/tesseract) et visualisation des artefacts de detection.",
    points: ["Upload vers /api/mlpdr/upload", "Resultat plaque + statut", "Apercu des artefacts images"],
  },
  {
    title: "Presentation projet",
    path: "/project",
    tag: "Projet",
    description:
      "Page de presentation institutionnelle du projet OCR/MLPDR avec overview, workflow, stack et CTA de navigation.",
    points: ["Architecture et objectifs", "Features et workflow", "Meme design system"],
  },
];

const endpoints = [
  { label: "Health OCR", url: "/health/ocr", note: "Proxy nginx (sante du service OCR)" },
  { label: "Health MLPDR", url: "/health/mlpdr", note: "Proxy nginx (sante du service plaques)" },
  { label: "API OCR", url: "/api/ocr/documents", note: "Liste des documents OCR" },
  { label: "API MLPDR", url: "/api/mlpdr/health", note: "Health endpoint du backend MLPDR" },
];

export default function TestsHub() {
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
              <li className="font-medium text-ink">Tests</li>
            </ol>
          </nav>

          <div className="hero-panel institution-card rounded-2xl border border-border p-6 sm:p-8">
            <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
              <div>
                <Badge tone="accent">Pages de test</Badge>
                <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">
                  Acces unifie aux tests reels OCR et MLPDR
                </h1>
                <p className="mt-4 max-w-3xl text-base leading-7 text-muted">
                  Ces pages utilisent le meme theme institutionnel que l&apos;accueil et consomment les APIs reelles du
                  projet (OCR documents et lecture de plaques MLPDR).
                </p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button to="/tests/ocr" size="lg">
                    Tester OCR Documents
                  </Button>
                  <Button to="/tests/mlpdr" variant="secondary" size="lg">
                    Tester MLPDR Plaques
                  </Button>
                </div>
              </div>

              <Card className="bg-white/80">
                <div className="space-y-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.08em] text-primary">Passerelles utiles</p>
                    <h2 className="mt-2 text-lg font-semibold text-ink">Interfaces existantes (legacy)</h2>
                    <p className="mt-2 text-sm leading-6 text-muted">
                      Liens directs vers les interfaces actuelles du monorepo, en complement des nouvelles pages
                      thematisees.
                    </p>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <a
                      href="http://localhost/ocr"
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-xl border border-border bg-surface p-4 transition hover:border-primary/25 hover:bg-primary/5"
                    >
                      <div className="text-sm font-semibold text-ink">Interface OCR existante</div>
                      <div className="mt-1 text-xs text-muted">http://localhost/ocr</div>
                    </a>
                    <a
                      href="http://localhost/mlpdr"
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-xl border border-border bg-surface p-4 transition hover:border-primary/25 hover:bg-primary/5"
                    >
                      <div className="text-sm font-semibold text-ink">Interface MLPDR existante</div>
                      <div className="mt-1 text-xs text-muted">http://localhost/mlpdr</div>
                    </a>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </Section>

      <Section tone="soft">
        <SectionTitle
          eyebrow="Modules"
          title="Pages de test disponibles"
          subtitle="Chaque page reprend la meme identite visuelle (header, sections, cards, tokens) et cible un module reel."
        />
        <div className="grid gap-4 lg:grid-cols-3">
          {testPages.map((item) => (
            <Card key={item.path} interactive className="flex h-full flex-col">
              <div className="flex items-center justify-between gap-3">
                <Badge tone="primary">{item.tag}</Badge>
                <span className="text-xs text-muted">{item.path}</span>
              </div>
              <h3 className="mt-4 text-lg font-semibold text-ink">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{item.description}</p>
              <ul className="mt-4 space-y-2">
                {item.points.map((point) => (
                  <li key={point} className="flex items-start gap-2 text-sm text-muted">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-5">
                <Button to={item.path} className="w-full justify-center">
                  Ouvrir
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </Section>

      <Section>
        <SectionTitle
          eyebrow="Endpoints"
          title="Raccourcis API / sante"
          subtitle="Points de verification utiles pendant les tests. Les liens s&apos;ouvrent dans un nouvel onglet."
        />
        <div className="grid gap-4 md:grid-cols-2">
          {endpoints.map((endpoint) => (
            <Card key={endpoint.url}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 className="text-base font-semibold text-ink">{endpoint.label}</h3>
                  <p className="mt-1 text-sm text-muted">{endpoint.note}</p>
                  <code className="mt-3 block rounded-md border border-border bg-surfaceSoft px-3 py-2 text-xs text-primary">
                    {endpoint.url}
                  </code>
                </div>
                <a
                  href={`http://localhost${endpoint.url}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex shrink-0 items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium text-primary hover:bg-primary/5"
                >
                  Ouvrir
                  <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden>
                    <path d="M7 13L13 7M9 7h4v4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                    <path d="M6 9v6h6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                  </svg>
                </a>
              </div>
            </Card>
          ))}
        </div>
      </Section>
    </>
  );
}
