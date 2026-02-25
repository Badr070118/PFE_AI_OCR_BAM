import Container from "./Container";

const footerGroups = [
  {
    title: "Portail",
    links: ["À propos", "Services", "Publications", "Données"],
  },
  {
    title: "Ressources",
    links: ["Documentation", "FAQ", "Centre d'assistance", "Plan du site"],
  },
  {
    title: "Légal",
    links: ["Mentions légales", "Confidentialité", "Accessibilité", "Conditions d'usage"],
  },
];

export default function Footer() {
  return (
    <footer className="mt-8 border-t border-border bg-surface">
      <Container className="py-10 sm:py-14">
        <div className="grid gap-10 lg:grid-cols-[1.2fr_2fr]">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-3 rounded-lg border border-border bg-page px-3 py-2">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary text-xs font-bold text-white">
                IM
              </span>
              <div>
                <p className="text-sm font-semibold text-primary">Institution du Maroc</p>
                <p className="text-xs text-muted">Portail institutionnel (maquette front-end)</p>
              </div>
            </div>
            <p className="max-w-md text-sm leading-6 text-muted">
              Interface de démonstration inspirée d’une architecture institutionnelle: navigation riche, accès rapide,
              publications et page projet, conçue pour une intégration React/Vite.
            </p>
            <div className="text-sm text-muted">
              <p>Contact : contact@institution.example</p>
              <p>Téléphone : +212 000 000 000</p>
              <p>Adresse : Rabat, Maroc (placeholder)</p>
            </div>
          </div>

          <div className="grid gap-8 sm:grid-cols-3">
            {footerGroups.map((group) => (
              <div key={group.title}>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.08em] text-primary">{group.title}</h2>
                <ul className="space-y-2">
                  {group.links.map((link) => (
                    <li key={link}>
                      <a href="#" className="text-sm text-muted transition hover:text-primary">
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-border pt-4 text-xs text-muted sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Portail institutionnel (prototype). Tous droits réservés.</p>
          <div className="flex items-center gap-2">
            {["X", "in", "yt"].map((label) => (
              <a
                key={label}
                href="#"
                aria-label={`Lien social ${label}`}
                className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border bg-page text-[11px] font-semibold text-primary hover:border-primary/40"
              >
                {label}
              </a>
            ))}
          </div>
        </div>
      </Container>
    </footer>
  );
}
