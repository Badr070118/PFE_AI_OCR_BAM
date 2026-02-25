import { useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import Container from "./Container";
import LanguageSwitch from "./LanguageSwitch";
import MegaMenu from "./MegaMenu";
import type { NavItem } from "../data/navigation";
import { navigation } from "../data/navigation";

type Lang = "FR" | "EN" | "ع";

function InstitutionMark() {
  return (
    <div className="flex items-center gap-4">
      <div className="relative h-14 w-14 shrink-0 rounded-md bg-accent/90 p-1 shadow-sm">
        <div className="absolute inset-0 rotate-45 rounded-md border border-white/25" />
        <svg viewBox="0 0 64 64" className="h-full w-full text-primary" aria-hidden>
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
        <p className="text-xs uppercase tracking-[0.18em] text-muted">Portail Institutionnel</p>
        <p className="text-lg font-semibold text-primary sm:text-xl">Institution du Maroc</p>
        <p className="text-xs text-muted">Interface de consultation & services numériques</p>
      </div>
    </div>
  );
}

function FacadeBannerArt() {
  return (
    <div className="relative hidden h-28 overflow-hidden rounded-xl border border-border/80 bg-[#efece6] md:block">
      <div className="absolute inset-0 glass-line opacity-70" />
      <svg viewBox="0 0 1200 240" className="absolute inset-0 h-full w-full" aria-hidden>
        <defs>
          <linearGradient id="roof" x1="0" x2="1">
            <stop offset="0%" stopColor="#835d39" />
            <stop offset="55%" stopColor="#a77d4e" />
            <stop offset="100%" stopColor="#744b30" />
          </linearGradient>
        </defs>
        <rect x="0" y="138" width="1200" height="102" fill="#e6e0d6" />
        <path d="M240 56 L620 28 L1015 55 L995 86 L258 84 Z" fill="url(#roof)" />
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
      <div className="absolute right-4 top-3 rounded-md bg-white/85 px-3 py-1 text-xs font-medium text-primary">
        Visuel institutionnel (inspiration)
      </div>
    </div>
  );
}

type MobilePanelProps = {
  items: NavItem[];
  open: boolean;
  onClose: () => void;
};

function MobileNavPanel({ items, open, onClose }: MobilePanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div
      className={[
        "lg:hidden overflow-hidden transition-[max-height,opacity] duration-300",
        open ? "max-h-[80vh] opacity-100" : "max-h-0 opacity-0",
      ].join(" ")}
      aria-hidden={!open}
    >
      <div className="mt-3 space-y-2 rounded-xl border border-border bg-surface p-3">
        {items.map((item) => {
          const hasMenu = Boolean(item.columns?.length);
          const isExpanded = expanded === item.label;
          if (!hasMenu && item.href) {
            return (
              <Link
                key={item.label}
                to={item.href}
                onClick={onClose}
                className="block rounded-lg border border-transparent px-3 py-2 text-sm font-medium text-ink hover:border-border hover:bg-surfaceSoft"
              >
                {item.label}
              </Link>
            );
          }

          return (
            <div key={item.label} className="rounded-lg border border-border/80 bg-white">
              <button
                type="button"
                onClick={() => setExpanded(isExpanded ? null : item.label)}
                aria-expanded={isExpanded}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium text-ink"
              >
                <span>{item.label}</span>
                <svg
                  viewBox="0 0 20 20"
                  className={`h-4 w-4 text-muted transition-transform ${isExpanded ? "rotate-180" : ""}`}
                  aria-hidden
                >
                  <path d="M5 7l5 6 5-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              </button>
              {isExpanded ? (
                <div className="space-y-3 border-t border-border/70 px-3 py-3">
                  {item.columns?.map((column) => (
                    <div key={column.title} className="space-y-1">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-primary">{column.title}</div>
                      {column.links.map((link) => (
                        <Link
                          key={link.label}
                          to={link.href}
                          onClick={onClose}
                          className="block rounded-md px-2 py-1.5 text-sm text-muted hover:bg-surfaceSoft hover:text-ink"
                        >
                          {link.label}
                        </Link>
                      ))}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Header() {
  const [lang, setLang] = useState<Lang>("FR");
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const location = useLocation();
  const headerRef = useRef<HTMLElement | null>(null);

  const currentMenu = useMemo(() => navigation.find((item) => item.label === openMenu), [openMenu]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
    setOpenMenu(null);
  }, [location.pathname]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpenMenu(null);
        setMobileOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <header ref={headerRef} className="sticky top-0 z-40 bg-page/95 backdrop-blur supports-[backdrop-filter]:bg-page/80">
      <div className={`border-b border-border/80 transition-shadow ${scrolled ? "nav-shadow" : ""}`}>
        <Container className="py-3">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <InstitutionMark />
              <div className="flex items-center justify-between gap-3 sm:justify-end">
                <div className="hidden items-center gap-3 text-xs text-muted sm:flex">
                  <span>Portail public</span>
                  <span className="h-1 w-1 rounded-full bg-border" />
                  <span>Navigation institutionnelle</span>
                </div>
                <LanguageSwitch value={lang} onChange={setLang} />
              </div>
            </div>
            <FacadeBannerArt />
          </div>
        </Container>
      </div>

      <div className="border-b border-border/70 bg-white/90">
        <Container>
          <div className="relative py-2">
            <div className="hidden items-center gap-1 lg:flex">
              {navigation.map((item) => {
                const hasMega = Boolean(item.columns?.length);
                const isOpen = openMenu === item.label;
                const isDirectActive = item.href ? location.pathname === item.href : false;

                if (!hasMega && item.href) {
                  return (
                    <NavLink
                      key={item.label}
                      to={item.href}
                      className={({ isActive }) =>
                        [
                          "rounded-md px-3 py-2 text-sm font-medium transition",
                          isActive || isDirectActive ? "bg-primary text-white" : "text-ink hover:bg-surfaceSoft",
                        ].join(" ")
                      }
                    >
                      {item.label}
                    </NavLink>
                  );
                }

                return (
                  <div
                    key={item.label}
                    className="relative"
                    onMouseEnter={() => setOpenMenu(item.label)}
                    onMouseLeave={() => setOpenMenu((value) => (value === item.label ? null : value))}
                  >
                    <button
                      type="button"
                      aria-expanded={isOpen}
                      aria-haspopup="menu"
                      onClick={() => setOpenMenu(isOpen ? null : item.label)}
                      onFocus={() => setOpenMenu(item.label)}
                      className={[
                        "inline-flex items-center gap-1 rounded-md px-3 py-2 text-sm font-medium transition",
                        isOpen ? "bg-primary text-white" : "text-ink hover:bg-surfaceSoft",
                      ].join(" ")}
                    >
                      <span>{item.label}</span>
                      <svg viewBox="0 0 20 20" className={`h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`} aria-hidden>
                        <path d="M5 7l5 6 5-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between gap-3 lg:hidden">
              <p className="text-sm font-medium text-primary">Navigation</p>
              <button
                type="button"
                onClick={() => setMobileOpen((v) => !v)}
                aria-expanded={mobileOpen}
                aria-controls="mobile-nav-panel"
                className="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm font-medium text-ink"
              >
                <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden>
                  {mobileOpen ? (
                    <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  ) : (
                    <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  )}
                </svg>
                Menu
              </button>
            </div>

            <div className="relative">
              {currentMenu ? <MegaMenu item={currentMenu} onClose={() => setOpenMenu(null)} /> : null}
            </div>

            <div id="mobile-nav-panel">
              <MobileNavPanel items={navigation} open={mobileOpen} onClose={() => setMobileOpen(false)} />
            </div>
          </div>
        </Container>
      </div>
    </header>
  );
}
