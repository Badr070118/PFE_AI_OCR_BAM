import Button from "../components/Button";
import Card from "../components/Card";
import Section from "../components/Section";
import SectionTitle from "../components/SectionTitle";
import Badge from "../components/Badge";
import { latestPublications, quickLinks, type QuickLink } from "../data/home";

function QuickIcon({ type }: { type: QuickLink["icon"] }) {
  const common = "h-5 w-5 text-primary";
  switch (type) {
    case "grid":
      return (
        <svg viewBox="0 0 24 24" className={common} aria-hidden>
          <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" fill="none" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      );
    case "document":
      return (
        <svg viewBox="0 0 24 24" className={common} aria-hidden>
          <path d="M7 3h7l5 5v13H7z" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="M14 3v6h6M9 13h8M9 17h6" fill="none" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      );
    case "chart":
      return (
        <svg viewBox="0 0 24 24" className={common} aria-hidden>
          <path d="M4 19h16M7 16V9M12 16V6M17 16v-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
    case "shield":
      return (
        <svg viewBox="0 0 24 24" className={common} aria-hidden>
          <path d="M12 3l7 3v6c0 4.7-2.7 7.9-7 9-4.3-1.1-7-4.3-7-9V6z" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="M9.5 12l1.8 1.8 3.7-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
    case "calendar":
      return (
        <svg viewBox="0 0 24 24" className={common} aria-hidden>
          <path d="M5 6h14v13H5zM8 3v4M16 3v4M5 10h14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
    case "layers":
      return (
        <svg viewBox="0 0 24 24" className={common} aria-hidden>
          <path d="M12 4l8 4-8 4-8-4 8-4zm0 8l8 4-8 4-8-4m8-4v8" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
    default:
      return null;
  }
}

function HeroIllustration() {
  return (
    <div className="hero-panel institution-card relative overflow-hidden rounded-2xl border border-border p-5 sm:p-7">
      <div className="paper-grid absolute inset-0 opacity-20" />
      <div className="relative space-y-5">
        <div className="flex items-center justify-between">
          <Badge tone="accent">Navigation & Services</Badge>
          <div className="inline-flex items-center gap-1 rounded-full border border-border bg-white/80 px-3 py-1 text-xs text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            Prototype UI
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-white/70 bg-white/85 p-4 backdrop-blur">
            <p className="text-xs uppercase tracking-[0.08em] text-muted">Accès rapide</p>
            <p className="mt-2 text-sm font-medium text-ink">Services, dossiers, tableaux et catalogues</p>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {Array.from({ length: 6 }).map((_, idx) => (
                <div key={idx} className="h-8 rounded-md border border-border bg-surfaceSoft" />
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-primary/10 bg-primary/[0.03] p-4">
            <p className="text-xs uppercase tracking-[0.08em] text-primary">Publications récentes</p>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              <li className="rounded-md bg-white/70 px-3 py-2">Note d'information - mise à jour</li>
              <li className="rounded-md bg-white/70 px-3 py-2">Rapport - performance des services</li>
              <li className="rounded-md bg-white/70 px-3 py-2">Guide - interopérabilité</li>
            </ul>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-white/70 p-4">
          <svg viewBox="0 0 680 160" className="h-28 w-full" aria-hidden>
            <path d="M20 130h640" stroke="rgb(203 213 225)" strokeWidth="2" />
            <path d="M90 90l110-32 120 18 120-28 120 18 55 24v40H90z" fill="rgb(213 198 168)" />
            <path d="M95 90h570v40H95z" fill="rgb(238 232 222)" />
            <path d="M105 84h548l-22-14H126z" fill="rgb(134 95 60)" />
            <g fill="rgb(125 94 64)">
              {Array.from({ length: 10 }).map((_, i) => (
                <rect key={i} x={120 + i * 48} y="98" width="10" height="32" rx="2" />
              ))}
            </g>
          </svg>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <>
      <Section className="pt-8 sm:pt-10">
        <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-start">
          <div className="space-y-6">
            <Badge tone="primary">Portail Institutionnel</Badge>
            <div className="space-y-4">
              <h1 className="max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-ink sm:text-5xl lg:text-[3.35rem]">
                Navigation institutionnelle moderne, sobre et orientée accès public.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-muted sm:text-lg">
                Maquette React inspirée d’un portail institutionnel premium : header structuré, mega-menu, rubriques
                d’accès rapide, publications et sections conçues pour une expérience claire sur tous les écrans.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button to="/tests" size="lg">
                Ouvrir le hub de tests
              </Button>
              <Button to="/tests/ocr" variant="secondary" size="lg">
                Tester OCR Documents
              </Button>
              <Button to="/tests/mlpdr" variant="ghost" size="lg">
                Tester MLPDR Plaques
              </Button>
            </div>
            <div className="grid gap-4 rounded-2xl border border-border bg-surface p-4 sm:grid-cols-3">
              {[
                ["24/7", "Disponibilité portail"],
                ["5 rubriques", "Navigation riche"],
                ["5 pages", "Prototype coherent"],
              ].map(([value, label]) => (
                <div key={label}>
                  <div className="text-2xl font-semibold text-primary">{value}</div>
                  <div className="text-sm text-muted">{label}</div>
                </div>
              ))}
            </div>
          </div>
          <HeroIllustration />
        </div>
      </Section>

      <Section id="quick-access" tone="soft">
        <SectionTitle
          eyebrow="Quick Access"
          title="Accès rapide"
          subtitle="Tuiles de navigation prioritaires pour orienter rapidement les usagers vers les services et ressources clés."
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {quickLinks.map((item) => (
            <a key={item.id} href={item.href} className="group">
              <Card interactive className="h-full">
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-primary/15 bg-primary/5">
                  <QuickIcon type={item.icon} />
                </div>
                <h3 className="text-base font-semibold text-ink transition group-hover:text-primary">{item.title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{item.description}</p>
                <div className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-primary">
                  Ouvrir
                  <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden>
                    <path d="M7 5l5 5-5 5M12 10H4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                  </svg>
                </div>
              </Card>
            </a>
          ))}
        </div>
      </Section>

      <Section>
        <SectionTitle
          eyebrow="Latest"
          title="Dernières publications"
          subtitle="Exemple de bloc éditorial institutionnel avec hiérarchie claire, tags et dates de publication."
          actions={<Button variant="secondary">Voir toutes les publications</Button>}
        />
        <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
          <div className="space-y-4">
            {latestPublications.map((item) => (
              <Card key={item.id} interactive className="p-4 sm:p-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone="muted">{item.tag}</Badge>
                      <span className="text-xs uppercase tracking-[0.08em] text-muted">{item.date}</span>
                    </div>
                    <h3 className="text-lg font-semibold leading-snug text-ink">{item.title}</h3>
                    <p className="text-sm leading-6 text-muted">{item.excerpt}</p>
                  </div>
                  <a
                    href={item.href}
                    className="inline-flex shrink-0 items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium text-primary hover:bg-primary/5"
                  >
                    Lire
                    <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden>
                      <path d="M7 5l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                    </svg>
                  </a>
                </div>
              </Card>
            ))}
          </div>

          <div className="space-y-4">
            <Card className="hero-panel">
              <div className="space-y-3">
                <Badge tone="accent">Accès prioritaire</Badge>
                <h3 className="text-lg font-semibold text-ink">Espace projet numérique</h3>
                <p className="text-sm leading-6 text-muted">
                  Présentation du projet OCR / lecture de plaques, architecture fonctionnelle et parcours de démonstration.
                </p>
                <div className="grid gap-2">
                  <Button to="/tests" className="w-full justify-center">
                    Ouvrir le hub de tests
                  </Button>
                  <div className="grid grid-cols-2 gap-2">
                    <Button to="/tests/ocr" variant="secondary" className="w-full justify-center">
                      OCR
                    </Button>
                    <Button to="/tests/mlpdr" variant="secondary" className="w-full justify-center">
                      MLPDR
                    </Button>
                  </div>
                  <Button to="/project" variant="ghost" className="w-full justify-center">
                    Consulter la page projet
                  </Button>
                </div>
              </div>
            </Card>

            <Card>
              <h3 className="text-sm font-semibold uppercase tracking-[0.08em] text-primary">Points d'information</h3>
              <ul className="mt-3 space-y-3 text-sm text-muted">
                <li className="rounded-lg border border-border bg-surfaceSoft p-3">Mises à jour du portail tous les mois.</li>
                <li className="rounded-lg border border-border bg-surfaceSoft p-3">Documentation et assistance centralisées.</li>
                <li className="rounded-lg border border-border bg-surfaceSoft p-3">Navigation conçue pour usage clavier et mobile.</li>
              </ul>
            </Card>
          </div>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="institution-card overflow-hidden rounded-2xl border border-primary/10 bg-institution-gradient text-white">
          <div className="grid gap-6 p-6 sm:p-8 lg:grid-cols-[1.2fr_auto] lg:items-center">
            <div>
              <p className="text-xs uppercase tracking-[0.14em] text-white/75">Call To Action</p>
              <h2 className="mt-2 text-2xl font-semibold leading-tight sm:text-3xl">
                Besoin d’un portail institutionnel moderne pour un projet métier ?
              </h2>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-white/80 sm:text-base">
                Ce prototype montre une base front-end réutilisable (design system, header à mega-menu, pages
                institutionnelles et page projet) prête à être adaptée à ton contenu réel.
              </p>
            </div>
            <div className="flex flex-wrap gap-3 lg:justify-end">
              <Button to="/tests" variant="secondary" className="border-white/20 bg-white/10 text-white hover:bg-white/15">
                Ouvrir les tests
              </Button>
              <Button to="/tests/ocr" className="bg-white text-primary hover:bg-white/90">
                Tester OCR
              </Button>
              <Button to="/tests/mlpdr" variant="secondary" className="border-white/20 bg-white/10 text-white hover:bg-white/15">
                Tester MLPDR
              </Button>
            </div>
          </div>
        </div>
      </Section>
    </>
  );
}
