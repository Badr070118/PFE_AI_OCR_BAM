import { useEffect, useState } from "react";
import "./app-shell.css";
import OcrPage from "./pages/OcrPage";
import MlpdrPage from "./pages/MlpdrPage";
import SmartParkingPage from "./pages/SmartParkingPage";

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
        <img src="/bam-logo.png" alt="" className="inst-brand-mark-img" loading="eager" decoding="async" />
      </div>
      <div className="inst-brand-copy">
        <p className="inst-brand-title">Bank Al-Maghrib</p>
        <p className="inst-brand-subtitle">OCR Documents & MLPDR Plaques</p>
      </div>
    </div>
  );
}

function FacadeBanner({ scrollProgress }) {
  return (
    <div className="inst-facade" aria-hidden style={{ "--facade-scroll": scrollProgress }}>
      <img
        src="/bam-facade-photo.jpg"
        alt=""
        className="inst-facade-photo"
        loading="eager"
        decoding="async"
        onError={(event) => {
          const img = event.currentTarget;
          if (img.dataset.fallbackApplied === "1") return;
          img.dataset.fallbackApplied = "1";
          img.src = "/bam-facade.svg";
        }}
      />
      <div className="inst-facade-overlay" />
      <div className="inst-facade-label">Siege Bank Al-Maghrib</div>
    </div>
  );
}

function ShellNav({ pathname }) {
  const items = [
    { key: "home", label: "Accueil", path: "/" },
    { key: "project", label: "Projet", path: "/project" },
    { key: "ocr", label: "OCR Documents", path: "/ocr" },
    { key: "parking", label: "Smart Parking", path: "/anpr" },
  ];

  const activeKey = pathname.startsWith("/anpr")
    ? "parking"
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
        <div className="inst-hero-grid inst-hero-grid-home">
          <div className="inst-hero-copy inst-hero-copy-home">
            <h1>Portail unifie pour OCR documents et lecture de plaques MLPDR.</h1>
            <p>
              Portail institutionnel unifie pour l'exploitation des modules OCR Documents et MLPDR Plaques, avec une
              navigation centralisee et une experience coherente sur l'ensemble des pages.
            </p>
            <div className="inst-cta-row">
              <button type="button" className="btn primary" onClick={() => navigate("/project")}>
                Voir la page projet
              </button>
              <button type="button" className="btn secondary" onClick={() => navigate("/ocr")}>
                Acceder a OCR Documents
              </button>
              <button type="button" className="btn ghost" onClick={() => navigate("/mlpdr")}>
                Acceder a MLPDR Plaques
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
                <strong>APIs operationnelles</strong>
                <span>/api/ocr et /api/mlpdr</span>
              </div>
            </div>
          </div>

        </div>
      </section>

      <section className="inst-section">
        <div className="inst-section-head">
          <div>
            <span className="inst-pill inst-pill-accent">Acces Modules</span>
            <h2>Acces rapide</h2>
            <p>Acces directs aux modules metier, aux points de supervision et aux ressources principales du projet.</p>
          </div>
        </div>
        <div className="inst-quick-grid">
          <QuickAccessTile title="OCR Documents" description="Upload, JSON, Llama, chat document." onClick={() => navigate("/ocr")} />
          <QuickAccessTile title="Smart Parking" description="Portail intelligent, logs et analytics." onClick={() => navigate("/anpr")} />
          <QuickAccessTile title="Page Projet" description="Architecture, workflow et acces modules." onClick={() => navigate("/project")} />
          <QuickAccessTile title="Sante OCR" description="Etat de service OCR via /health/ocr." onClick={() => window.open("/health/ocr", "_blank")} />
          <QuickAccessTile title="Sante MLPDR" description="Etat de service plaques via /health/mlpdr." onClick={() => window.open("/health/mlpdr", "_blank")} />
          <QuickAccessTile title="Documents OCR" description="Consultation de la liste des documents OCR en base." onClick={() => window.open("/api/ocr/documents", "_blank")} />
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
                Portail institutionnel unifie pour les flux OCR Documents et MLPDR Plaques, connecte aux APIs metier
                via la passerelle Nginx de la plateforme.
              </p>
              <div className="inst-cta-row">
                <button type="button" className="btn primary" onClick={() => navigate("/ocr")}>
                  Ouvrir OCR Documents
                </button>
                <button type="button" className="btn secondary" onClick={() => navigate("/anpr")}>
                  Ouvrir Smart Parking
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
                  Ouvrir OCR Documents
                </button>
                <button type="button" className="btn secondary" onClick={() => navigate("/anpr")}>
                  Ouvrir Smart Parking
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="inst-section">
        <div className="inst-section-head">
          <div>
            <span className="inst-pill inst-pill-primary">Modules metier</span>
            <h2>Acces directs aux modules</h2>
            <p>Acces aux fonctionnalites OCR Documents et MLPDR Plaques depuis un portail institutionnel unifie.</p>
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
            <span className="inst-pill inst-pill-primary">Parking</span>
            <h3>Smart Parking</h3>
            <p>Simulation portail intelligent, detection plaque et suivi des acces.</p>
            <button type="button" className="btn primary" onClick={() => navigate("/anpr")}>
              Aller a Smart Parking
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
  if (pathname.startsWith("/anpr")) return <SmartParkingPage />;

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
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    let rafId = 0;

    const updateScroll = () => {
      rafId = 0;
      setScrollY(window.scrollY || 0);
    };

    const onScroll = () => {
      if (rafId) return;
      rafId = window.requestAnimationFrame(updateScroll);
    };

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    return () => {
      window.removeEventListener("scroll", onScroll);
      if (rafId) window.cancelAnimationFrame(rafId);
    };
  }, []);

  const facadeScrollProgress = Math.min(scrollY / 220, 1);

  return (
    <div className="shell">
      <header className="shell-header" role="banner">
        <div className="shell-topbar-wrap">
          <div className="shell-topbar">
            <InstitutionMark />
            <div className="shell-topbar-right">
              <div className="shell-topbar-meta">
                <span>Plateforme metier</span>
                <span className="dot" />
                <span>Exploitation institutionnelle</span>
              </div>
              <LanguageSwitch />
            </div>
          </div>
          <FacadeBanner scrollProgress={facadeScrollProgress} />
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
              <span className="shell-footer-brand-icon">BAM</span>
              <div>
                <strong>Bank Al-Maghrib</strong>
                <p>Portail OCR / MLPDR institutionnel</p>
              </div>
            </div>
            <p className="shell-footer-text">
              Interface unifiee d'exploitation pour les modules OCR Documents et MLPDR Plaques, connectee aux APIs
              metier de la plateforme via la passerelle institutionnelle.
            </p>
            <div className="shell-footer-social">
              <p className="shell-footer-col-title">Nos reseaux sociaux / Application mobile</p>
              <div className="shell-footer-social-row" aria-label="Reseaux sociaux et application mobile">
                <a href="#" className="shell-footer-social-link" aria-label="X" onClick={(e) => e.preventDefault()}>X</a>
                <a href="#" className="shell-footer-social-link" aria-label="LinkedIn" onClick={(e) => e.preventDefault()}>in</a>
                <a href="#" className="shell-footer-social-link" aria-label="YouTube" onClick={(e) => e.preventDefault()}>YT</a>
                <a href="#" className="shell-footer-social-link" aria-label="Facebook" onClick={(e) => e.preventDefault()}>f</a>
                <a href="#" className="shell-footer-social-link" aria-label="Instagram" onClick={(e) => e.preventDefault()}>ig</a>
                <a href="#" className="shell-footer-social-link" aria-label="Application mobile" onClick={(e) => e.preventDefault()}>app</a>
              </div>
            </div>
          </div>

          <div className="shell-footer-contact">
            <p className="shell-footer-col-title">Toujours a votre ecoute</p>
            <ul className="shell-footer-list">
              <li><a href="#" onClick={(e) => e.preventDefault()}>Localisez nous</a></li>
              <li><a href="#" onClick={(e) => e.preventDefault()}>Nous contacter</a></li>
              <li><a href="/health/ocr" target="_blank" rel="noreferrer">Etat du service OCR</a></li>
              <li><a href="/health/mlpdr" target="_blank" rel="noreferrer">Etat du service MLPDR</a></li>
            </ul>
          </div>
        </div>
        <div className="shell-footer-bottom">
          <span>Copyright 2026 Bank Al-Maghrib</span>
          <div className="shell-footer-legal-links">
            <a href="/" onClick={(e) => { e.preventDefault(); navigate("/"); }}>Plan de site</a>
            <a href="#" onClick={(e) => e.preventDefault()}>Mentions legales</a>
            <a href="#" onClick={(e) => e.preventDefault()}>Contactez nous</a>
            <a href="/project" onClick={(e) => { e.preventDefault(); navigate("/project"); }}>Liens utiles</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
