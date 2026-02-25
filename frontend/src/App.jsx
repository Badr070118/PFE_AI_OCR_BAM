import { useEffect, useMemo, useState } from "react";
import "./app-shell.css";
import OcrPage from "./pages/OcrPage";
import MlpdrPage from "./pages/MlpdrPage";

function usePathname() {
  const [pathname, setPathname] = useState(window.location.pathname);

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return pathname;
}

function navigate(pathname, options = {}) {
  const replace = options.replace === true;
  if (window.location.pathname === pathname) return;
  if (replace) {
    window.history.replaceState({}, "", pathname);
  } else {
    window.history.pushState({}, "", pathname);
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function LanguageSwitch() {
  const [value, setValue] = useState("FR");

  return (
    <div className="inst-lang-switch" role="group" aria-label="Language switch">
      {["FR", "EN", "ع"].map((lang) => (
        <button
          key={lang}
          type="button"
          className={`inst-lang-btn ${value === lang ? "active" : ""}`}
          aria-pressed={value === lang}
          onClick={() => setValue(lang)}
        >
          {lang}
        </button>
      ))}
    </div>
  );
}

function InstitutionMark() {
  return (
    <div className="inst-brand">
      <div className="inst-brand-mark" aria-hidden>
        <svg viewBox="0 0 64 64" className="inst-brand-mark-svg">
          <path
            d="M14 40c6-1 10-5 12-10 2-5 6-8 12-9 7-1 11 2 12 6 1 4-2 8-6 10-5 2-10 0-14 2-5 2-8 7-16 7z"
            fill="currentColor"
            opacity=".95"
          />
          <path d="M22 17c2 5 8 8 14 9" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" />
          <path d="M28 28c6-2 11 1 12 6" stroke="#fff" strokeWidth="2" fill="none" strokeLinecap="round" opacity=".8" />
        </svg>
      </div>
      <div>
        <p className="inst-brand-eyebrow">Portail Institutionnel</p>
        <p className="inst-brand-title">Institution du Maroc</p>
        <p className="inst-brand-subtitle">OCR Documents & MLPDR Plaques</p>
      </div>
    </div>
  );
}

function FacadeBanner() {
  return (
    <div className="inst-facade" aria-hidden>
      <div className="inst-facade-overlay" />
      <svg viewBox="0 0 1200 240" className="inst-facade-svg">
        <defs>
          <linearGradient id="roof-grad" x1="0" x2="1">
            <stop offset="0%" stopColor="#7d5b38" />
            <stop offset="55%" stopColor="#a87e4f" />
            <stop offset="100%" stopColor="#7a5334" />
          </linearGradient>
        </defs>
        <rect x="0" y="138" width="1200" height="102" fill="#e6e0d6" />
        <path d="M240 56 L620 28 L1015 55 L995 86 L258 84 Z" fill="url(#roof-grad)" />
        <path d="M270 84 h700 v94 h-700z" fill="#d8c5a1" />
        <path d="M295 84 h310 v94 h-310z" fill="#b59162" opacity=".85" />
        <path d="M620 84 h145 v94 h-145z" fill="#efe9de" />
        <g fill="#87643f">
          <rect x="340" y="100" width="20" height="78" />
          <rect x="390" y="100" width="20" height="78" />
          <rect x="440" y="100" width="20" height="78" />
          <rect x="490" y="100" width="20" height="78" />
          <rect x="540" y="100" width="20" height="78" />
          <rect x="670" y="103" width="18" height="75" />
          <rect x="705" y="103" width="18" height="75" />
        </g>
        <g fill="none" stroke="#6a4a2c" strokeWidth="3" opacity=".75">
          <path d="M300 94 q18 8 36 0 q18-8 36 0 q18 8 36 0 q18-8 36 0 q18 8 36 0" />
          <path d="M300 114 q18 8 36 0 q18-8 36 0 q18 8 36 0 q18-8 36 0 q18 8 36 0" />
          <path d="M300 134 q18 8 36 0 q18-8 36 0 q18 8 36 0 q18-8 36 0 q18 8 36 0" />
        </g>
        <path d="M648 178 q44-92 88 0" fill="#d5c3a2" stroke="#8d6a44" strokeWidth="4" />
        <rect x="662" y="118" width="60" height="60" fill="#f3eee4" stroke="#8d6a44" strokeWidth="3" />
      </svg>
      <div className="inst-facade-label">Visuel institutionnel (inspiration)</div>
    </div>
  );
}

function ShellNav({ pathname }) {
  const items = [
    { key: "home", label: "Accueil", path: "/" },
    { key: "project", label: "Projet", path: "/project" },
    { key: "ocr", label: "OCR Documents", path: "/ocr" },
    { key: "mlpdr", label: "MLPDR Plaques", path: "/mlpdr" },
  ];

  const activeKey = pathname.startsWith("/mlpdr") || pathname.startsWith("/anpr")
    ? "mlpdr"
    : pathname.startsWith("/ocr")
    ? "ocr"
    : pathname.startsWith("/project")
    ? "project"
    : "home";

  return (
    <div className="inst-navbar-row">
      <nav className="inst-navbar" aria-label="Navigation principale">
        {items.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`inst-nav-item ${activeKey === item.key ? "active" : ""}`}
            onClick={() => navigate(item.path)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="inst-navbar-tools">
        <button type="button" className="inst-mini-btn" onClick={() => navigate("/ocr")}>
          Test OCR
        </button>
        <button type="button" className="inst-mini-btn" onClick={() => navigate("/mlpdr")}>
          Test MLPDR
        </button>
      </div>
    </div>
  );
}

function QuickAccessTile({ title, description, onClick }) {
  return (
    <button type="button" className="inst-quick-tile" onClick={onClick}>
      <span className="inst-quick-icon" aria-hidden>
        <svg viewBox="0 0 24 24">
          <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" fill="none" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      </span>
      <span className="inst-quick-title">{title}</span>
      <span className="inst-quick-desc">{description}</span>
      <span className="inst-quick-link">Ouvrir</span>
    </button>
  );
}

function HomeLanding() {
  return (
    <div className="inst-page">
      <section className="inst-hero-panel">
        <div className="inst-hero-grid">
          <div className="inst-hero-copy">
            <span className="inst-pill inst-pill-primary">Portail Institutionnel</span>
            <h1>Portail unifie pour OCR documents et lecture de plaques MLPDR.</h1>
            <p>
              Interface institutionnelle reelle de la plateforme. Accede aux modules OCR et MLPDR depuis une navigation
              unique, avec le meme theme visuel sur toutes les pages.
            </p>
            <div className="inst-cta-row">
              <button type="button" className="btn primary" onClick={() => navigate("/project")}>
                Voir la page projet
              </button>
              <button type="button" className="btn secondary" onClick={() => navigate("/ocr")}>
                Tester OCR Documents
              </button>
              <button type="button" className="btn ghost" onClick={() => navigate("/mlpdr")}>
                Tester MLPDR Plaques
              </button>
            </div>
            <div className="inst-stats">
              <div>
                <strong>2 modules</strong>
                <span>OCR + MLPDR</span>
              </div>
              <div>
                <strong>1 portail</strong>
                <span>Theme institutionnel unifie</span>
              </div>
              <div>
                <strong>APIs reelles</strong>
                <span>/api/ocr et /api/mlpdr</span>
              </div>
            </div>
          </div>

          <div className="inst-hero-visual">
            <div className="inst-visual-card">
              <div className="inst-visual-head">
                <span className="inst-pill inst-pill-accent">Acces rapide</span>
                <span className="inst-visual-dot">Prototype UI</span>
              </div>
              <div className="inst-visual-panels">
                <div className="inst-visual-block">
                  <p>Modules actifs</p>
                  <ul>
                    <li>OCR Documents (upload + structuration + chat)</li>
                    <li>MLPDR Plaques (upload + detection + artefacts)</li>
                  </ul>
                </div>
                <div className="inst-visual-block soft">
                  <p>Navigation</p>
                  <div className="inst-visual-grid">
                    {Array.from({ length: 6 }).map((_, idx) => (
                      <span key={idx} />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="inst-section">
        <div className="inst-section-head">
          <div>
            <span className="inst-pill inst-pill-accent">Quick Access</span>
            <h2>Acces rapide</h2>
            <p>Tuiles directes vers les pages reelles de test et de presentation du projet.</p>
          </div>
        </div>
        <div className="inst-quick-grid">
          <QuickAccessTile title="OCR Documents" description="Upload, JSON, Llama, chat document." onClick={() => navigate("/ocr")} />
          <QuickAccessTile title="MLPDR Plaques" description="Detection plaque et artefacts images." onClick={() => navigate("/mlpdr")} />
          <QuickAccessTile title="Page Projet" description="Overview, workflow et acces modules." onClick={() => navigate("/project")} />
          <QuickAccessTile title="Health OCR" description="Verifier le backend OCR via /health/ocr." onClick={() => window.open("/health/ocr", "_blank")} />
          <QuickAccessTile title="Health MLPDR" description="Verifier le backend plaques via /health/mlpdr." onClick={() => window.open("/health/mlpdr", "_blank")} />
          <QuickAccessTile title="API OCR Docs" description="Liste des documents OCR en base." onClick={() => window.open("/api/ocr/documents", "_blank")} />
        </div>
      </section>
    </div>
  );
}

function ProjectLanding() {
  return (
    <div className="inst-page">
      <section className="inst-project-hero">
        <div className="inst-breadcrumb">
          <button type="button" onClick={() => navigate("/")}>Accueil</button>
          <span>/</span>
          <span>Projet</span>
        </div>
        <div className="inst-hero-panel">
          <div className="inst-hero-grid">
            <div className="inst-hero-copy">
              <span className="inst-pill inst-pill-accent">Page Projet</span>
              <h1>Plateforme OCR & Lecture de Plaques</h1>
              <p>
                Portail unifie pour les tests metier OCR documents et MLPDR plaques, relie aux APIs reelles via la
                passerelle nginx existante.
              </p>
              <div className="inst-cta-row">
                <button type="button" className="btn primary" onClick={() => navigate("/ocr")}>
                  Ouvrir OCR Documents
                </button>
                <button type="button" className="btn secondary" onClick={() => navigate("/mlpdr")}>
                  Ouvrir MLPDR Plaques
                </button>
                <button type="button" className="btn ghost" onClick={() => navigate("/")}>
                  Retour accueil
                </button>
              </div>
            </div>
            <div className="inst-project-card">
              <div className="inst-project-card-grid">
                <div>
                  <span>Modules</span>
                  <strong>OCR + MLPDR</strong>
                </div>
                <div>
                  <span>Frontend</span>
                  <strong>React (Vite)</strong>
                </div>
                <div>
                  <span>Backend</span>
                  <strong>FastAPI</strong>
                </div>
                <div>
                  <span>Passerelle</span>
                  <strong>Nginx + Docker</strong>
                </div>
              </div>
              <div className="inst-project-actions">
                <button type="button" className="btn primary" onClick={() => navigate("/ocr")}>
                  Tester OCR maintenant
                </button>
                <button type="button" className="btn secondary" onClick={() => navigate("/mlpdr")}>
                  Tester MLPDR maintenant
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="inst-section">
        <div className="inst-section-head">
          <div>
            <span className="inst-pill inst-pill-primary">Modules reels</span>
            <h2>Acces directs aux pages de test</h2>
            <p>Les contenus metier restent identiques, seul le theme visuel est harmonise avec la page d'accueil.</p>
          </div>
        </div>
        <div className="inst-project-modules">
          <article className="inst-module-card">
            <span className="inst-pill inst-pill-primary">OCR</span>
            <h3>OCR Documents</h3>
            <p>Upload de PDF/images, liste documents, structuration Llama 3.1 8B et chat sur document.</p>
            <button type="button" className="btn primary" onClick={() => navigate("/ocr")}>
              Aller a OCR
            </button>
          </article>
          <article className="inst-module-card">
            <span className="inst-pill inst-pill-primary">MLPDR</span>
            <h3>MLPDR Plaques</h3>
            <p>Detection/lecture de plaques, modes OCR (trained/tesseract) et visualisation des artefacts.</p>
            <button type="button" className="btn primary" onClick={() => navigate("/mlpdr")}>
              Aller a MLPDR
            </button>
          </article>
        </div>
      </section>
    </div>
  );
}

function RouteView({ pathname }) {
  if (pathname === "/" || pathname === "") return <HomeLanding />;
  if (pathname === "/project" || pathname === "/project/") return <ProjectLanding />;

  if (pathname.startsWith("/tests/ocr")) {
    navigate("/ocr", { replace: true });
    return null;
  }
  if (pathname.startsWith("/tests/mlpdr")) {
    navigate("/mlpdr", { replace: true });
    return null;
  }
  if (pathname === "/tests" || pathname === "/tests/") {
    navigate("/project", { replace: true });
    return null;
  }

  if (pathname.startsWith("/ocr")) return <OcrPage />;
  if (pathname.startsWith("/anpr")) {
    navigate("/mlpdr", { replace: true });
    return null;
  }
  if (pathname.startsWith("/mlpdr")) return <MlpdrPage />;

  return (
    <div className="inst-page">
      <section className="panel">
        <div className="panel-header">
          <h2>Route introuvable</h2>
          <p>La route demandee n'existe pas dans ce portail.</p>
        </div>
        <div className="inst-cta-row">
          <button type="button" className="btn primary" onClick={() => navigate("/")}>
            Retour accueil
          </button>
          <button type="button" className="btn secondary" onClick={() => navigate("/project")}>
            Page projet
          </button>
        </div>
      </section>
    </div>
  );
}

export default function App() {
  const pathname = usePathname();

  return (
    <div className="shell">
      <header className="shell-header" role="banner">
        <div className="shell-topbar-wrap">
          <div className="shell-topbar">
            <InstitutionMark />
            <div className="shell-topbar-right">
              <div className="shell-topbar-meta">
                <span>Portail public</span>
                <span className="dot" />
                <span>Navigation institutionnelle</span>
              </div>
              <LanguageSwitch />
            </div>
          </div>
          <FacadeBanner />
        </div>
        <div className="shell-nav-wrap">
          <ShellNav pathname={pathname} />
        </div>
      </header>

      <main className="shell-main" id="main-content">
        <RouteView pathname={pathname} />
      </main>

      <footer className="shell-footer">
        <div className="shell-footer-grid">
          <div>
            <div className="shell-footer-brand">
              <span className="shell-footer-brand-icon">IM</span>
              <div>
                <strong>Institution du Maroc</strong>
                <p>Portail OCR / MLPDR (frontend reel)</p>
              </div>
            </div>
            <p className="shell-footer-text">
              Interface unifiee de demonstration et de test pour les modules OCR Documents et MLPDR Plaques, connectee
              aux APIs reelles de la plateforme.
            </p>
          </div>

          <div className="shell-footer-links">
            <button type="button" onClick={() => navigate("/")}>Accueil</button>
            <button type="button" onClick={() => navigate("/project")}>Projet</button>
            <button type="button" onClick={() => navigate("/ocr")}>OCR Documents</button>
            <button type="button" onClick={() => navigate("/mlpdr")}>MLPDR Plaques</button>
          </div>
        </div>
        <div className="shell-footer-bottom">
          <span>© 2026 Portail institutionnel OCR / MLPDR</span>
          <span>FR / EN / ع</span>
        </div>
      </footer>
    </div>
  );
}
