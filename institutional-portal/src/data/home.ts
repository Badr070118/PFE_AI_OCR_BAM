export type QuickLink = {
  id: string;
  title: string;
  description: string;
  href: string;
  icon: "grid" | "document" | "chart" | "shield" | "calendar" | "layers";
};

export type PublicationItem = {
  id: string;
  date: string;
  tag: string;
  title: string;
  excerpt: string;
  href: string;
};

export const quickLinks: QuickLink[] = [
  {
    id: "tests-hub",
    title: "Hub de tests",
    description: "Acceder au point d'entree des pages de test OCR, MLPDR et presentation projet.",
    href: "/tests",
    icon: "grid",
  },
  {
    id: "ocr-documents",
    title: "Test OCR Documents",
    description: "Uploader un document, lancer la structuration Llama et tester le chat sur document.",
    href: "/tests/ocr",
    icon: "document",
  },
  {
    id: "mlpdr-plates",
    title: "Test MLPDR Plaques",
    description: "Tester la detection et la lecture de plaques avec artefacts de traitement.",
    href: "/tests/mlpdr",
    icon: "chart",
  },
  {
    id: "project-page",
    title: "Page projet",
    description: "Consulter la presentation fonctionnelle du projet OCR / MLPDR et son architecture.",
    href: "/project",
    icon: "shield",
  },
  {
    id: "agenda",
    title: "Agenda public",
    description: "Suivre les rendez-vous, sessions d'information et publications prevues.",
    href: "#",
    icon: "calendar",
  },
  {
    id: "catalog",
    title: "Catalogues de donnees",
    description: "Explorer les jeux de donnees, metadonnees et formats d'echange.",
    href: "#",
    icon: "layers",
  },
];

export const latestPublications: PublicationItem[] = [
  {
    id: "pub-1",
    date: "25 fev. 2026",
    tag: "Note",
    title: "Cadre de modernisation des services documentaires",
    excerpt: "Presentation des axes d'amelioration des parcours de consultation et d'archivage numerique.",
    href: "#",
  },
  {
    id: "pub-2",
    date: "20 fev. 2026",
    tag: "Rapport",
    title: "Suivi des performances des canaux digitaux",
    excerpt: "Indicateurs de disponibilite, temps de reponse et satisfaction sur les services prioritaires.",
    href: "#",
  },
  {
    id: "pub-3",
    date: "14 fev. 2026",
    tag: "Donnees",
    title: "Mise a jour des series publiques trimestrielles",
    excerpt: "Nouvelles series consolidees et revision de certaines metadonnees descriptives.",
    href: "#",
  },
  {
    id: "pub-4",
    date: "07 fev. 2026",
    tag: "Guide",
    title: "Bonnes pratiques d'echange inter-applicatif",
    excerpt: "Recommandations de securite, versioning et formats pour les integrations.",
    href: "#",
  },
  {
    id: "pub-5",
    date: "31 janv. 2026",
    tag: "Communique",
    title: "Evolution de l'experience portail institutionnel",
    excerpt: "Nouvelles rubriques d'acces rapide et navigation enrichie pour les usagers.",
    href: "#",
  },
];
