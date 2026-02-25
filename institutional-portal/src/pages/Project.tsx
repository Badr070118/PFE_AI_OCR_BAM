import { Link } from "react-router-dom";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Card from "../components/Card";
import Section from "../components/Section";
import SectionTitle from "../components/SectionTitle";
import { projectFeatures, projectOverview, techStack, workflowSteps } from "../data/project";

const moduleAccess = [
  {
    title: "OCR Documents",
    description: "Upload de documents, structuration Llama 3.1 8B, sauvegarde JSON et chat sur document.",
    path: "/tests/ocr",
    badge: "OCR",
  },
  {
    title: "MLPDR Plaques",
    description: "Test du nouveau projet plaques (MLPDR) avec upload image, lecture et artefacts.",
    path: "/tests/mlpdr",
    badge: "MLPDR",
  },
];

export default function Project() {
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
              <li className="font-medium text-ink">Projet</li>
            </ol>
          </nav>

          <div className="hero-panel institution-card rounded-2xl border border-border p-6 sm:p-8">
            <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
              <div>
                <Badge tone="accent">Page Projet</Badge>
                <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">
                  {projectOverview.title}
                </h1>
                <p className="mt-4 text-base leading-7 text-muted">{projectOverview.summary}</p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button to="/tests/ocr" size="lg">
                    Tester OCR Documents
                  </Button>
                  <Button to="/tests/mlpdr" variant="secondary" size="lg">
                    Tester MLPDR Plaques
                  </Button>
                  <Button to="/tests" variant="ghost" size="lg">
                    Hub de tests
                  </Button>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-white/80 p-4 sm:p-5">
                <p className="text-xs uppercase tracking-[0.08em] text-primary">Contexte</p>
                <p className="mt-3 text-sm leading-6 text-muted">{projectOverview.context}</p>
                <div className="mt-5 grid grid-cols-2 gap-3">
                  {[
                    ["Modules", "OCR + MLPDR"],
                    ["Interface", "React + Vite"],
                    ["APIs", "FastAPI"],
                    ["Deploiement", "Docker"],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-lg border border-border bg-surfaceSoft p-3">
                      <div className="text-xs uppercase tracking-[0.07em] text-muted">{label}</div>
                      <div className="mt-1 text-sm font-semibold text-ink">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </Section>

      <Section tone="soft">
        <SectionTitle
          eyebrow="Tests"
          title="Acces directs aux modules"
          subtitle="Depuis cette page projet, ouvre directement les interfaces de test OCR Documents et MLPDR Plaques."
        />
        <div className="grid gap-4 md:grid-cols-2">
          {moduleAccess.map((item) => (
            <Card key={item.path} interactive>
              <div className="flex items-center justify-between gap-3">
                <Badge tone="primary">{item.badge}</Badge>
                <span className="text-xs text-muted">{item.path}</span>
              </div>
              <h3 className="mt-4 text-lg font-semibold text-ink">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{item.description}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button to={item.path}>Ouvrir la page</Button>
                <Button to="/tests" variant="secondary">
                  Hub de tests
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </Section>

      <Section>
        <SectionTitle
          eyebrow="Overview"
          title="Vue d'ensemble"
          subtitle="Architecture pensee pour demontrer un parcours metier complet depuis la capture jusqu'a l'exploitation des donnees."
        />
        <div className="grid gap-5 md:grid-cols-2">
          <Card>
            <h3 className="text-lg font-semibold text-ink">Objectif produit</h3>
            <p className="mt-3 text-sm leading-6 text-muted">
              Fournir une interface unifiee pour l'analyse documentaire (OCR) et la lecture de plaques (MLPDR), avec
              resultats visualisables, persistance en base et exposition API pour integration.
            </p>
          </Card>
          <Card>
            <h3 className="text-lg font-semibold text-ink">Valeur operationnelle</h3>
            <p className="mt-3 text-sm leading-6 text-muted">
              Reduire les taches manuelles de saisie, accelerer le controle, standardiser les formats de sortie et
              faciliter l'exploitation par les equipes metier ou les systemes tiers.
            </p>
          </Card>
        </div>
      </Section>

      <Section>
        <SectionTitle
          eyebrow="Features"
          title="Fonctionnalites principales"
          subtitle="Cartes de capacite pour presenter clairement les briques de la plateforme."
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {projectFeatures.map((feature) => (
            <Card key={feature.title} interactive>
              <div className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-primary/5 text-primary">
                <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden>
                  <path
                    d="M4 10l4 4 8-8"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <h3 className="mt-4 text-base font-semibold text-ink">{feature.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{feature.description}</p>
            </Card>
          ))}
        </div>
      </Section>

      <Section tone="soft">
        <SectionTitle
          eyebrow="Workflow"
          title="Workflow"
          subtitle="Timeline en 4 etapes pour illustrer le parcours fonctionnel du projet."
        />
        <div className="relative">
          <div className="absolute left-6 top-0 hidden h-full w-px bg-border md:block" aria-hidden />
          <div className="space-y-4">
            {workflowSteps.map((item) => (
              <div key={item.step} className="grid gap-4 md:grid-cols-[64px_1fr] md:items-start">
                <div className="flex md:justify-center">
                  <div className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-accent/35 bg-white text-sm font-semibold text-primary shadow-sm">
                    {item.step}
                  </div>
                </div>
                <Card>
                  <h3 className="text-base font-semibold text-ink">{item.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted">{item.description}</p>
                </Card>
              </div>
            ))}
          </div>
        </div>
      </Section>

      <Section>
        <SectionTitle
          eyebrow="Tech Stack"
          title="Stack technique"
          subtitle="Badges reutilisables pour exposer les technologies utilisees."
        />
        <div className="flex flex-wrap gap-2">
          {techStack.map((tech) => (
            <Badge key={tech} tone="primary" className="text-[11px]">
              {tech}
            </Badge>
          ))}
        </div>
      </Section>

      <Section className="pt-0">
        <div className="institution-card rounded-2xl border border-border bg-surface p-6 sm:p-8">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-3xl">
              <Badge tone="accent">CTA</Badge>
              <h2 className="mt-3 text-2xl font-semibold text-ink sm:text-3xl">
                Pret pour une demo ou une adaptation projet
              </h2>
              <p className="mt-3 text-sm leading-6 text-muted sm:text-base">
                Le theme, les composants et la structure des pages sont concus pour etre reutilises sur un portail
                institutionnel reel, avec contenu metier, APIs et workflows specifiques.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button to="/tests/ocr">Tester OCR Documents</Button>
              <Button to="/tests/mlpdr" variant="secondary">
                Tester MLPDR Plaques
              </Button>
              <Button to="/tests" variant="ghost">
                Hub de tests
              </Button>
            </div>
          </div>
        </div>
      </Section>
    </>
  );
}
