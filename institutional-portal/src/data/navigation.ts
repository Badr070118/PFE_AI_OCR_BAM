export type NavLinkItem = {
  label: string;
  href: string;
  description?: string;
};

export type NavColumn = {
  title: string;
  links: NavLinkItem[];
};

export type NavItem = {
  label: string;
  href?: string;
  description?: string;
  columns?: NavColumn[];
};

export const navigation: NavItem[] = [
  {
    label: "A propos",
    columns: [
      {
        title: "Institution",
        links: [
          { label: "Mission et mandat", href: "#", description: "Cadre d'action et priorites publiques." },
          { label: "Gouvernance", href: "#", description: "Organisation, comites et responsabilites." },
          { label: "Strategie", href: "#", description: "Orientations pluriannuelles et feuille de route." },
        ],
      },
      {
        title: "Transparence",
        links: [
          { label: "Rapports institutionnels", href: "#", description: "Publications annuelles et bilans." },
          { label: "Marches publics", href: "#", description: "Procedures et avis en cours." },
          { label: "Questions frequentes", href: "#", description: "Reponses sur les services et demarches." },
        ],
      },
    ],
  },
  {
    label: "Services",
    columns: [
      {
        title: "Portail",
        links: [
          { label: "Acces professionnels", href: "#", description: "Espaces securises et formulaires." },
          { label: "Demandes en ligne", href: "#", description: "Soumission et suivi des dossiers." },
          { label: "Referentiels", href: "#", description: "Cadres techniques et formats d'echange." },
        ],
      },
      {
        title: "Accompagnement",
        links: [
          { label: "Documentation utilisateur", href: "#", description: "Guides de prise en main." },
          { label: "Centre d'assistance", href: "#", description: "Canaux de support et contacts." },
          { label: "Calendrier de service", href: "#", description: "Mises a jour et fenetres de maintenance." },
        ],
      },
    ],
  },
  {
    label: "Publications",
    columns: [
      {
        title: "Actualites",
        links: [
          { label: "Communiques", href: "#", description: "Annonces officielles et notes." },
          { label: "Dossiers thematiques", href: "#", description: "Analyses synthetiques par sujet." },
          { label: "Agenda", href: "#", description: "Evenements et prises de parole." },
        ],
      },
      {
        title: "Ressources",
        links: [
          { label: "Bibliotheque numerique", href: "#", description: "Documents et archives consultables." },
          { label: "Jeux de donnees", href: "#", description: "Exports structures et series." },
          { label: "Bulletins", href: "#", description: "Publications periodiques." },
        ],
      },
    ],
  },
  {
    label: "Donnees",
    columns: [
      {
        title: "Tableaux",
        links: [
          { label: "Indicateurs cles", href: "#", description: "Vue d'ensemble des chiffres de suivi." },
          { label: "Series chronologiques", href: "#", description: "Historique et comparaisons." },
          { label: "API et formats", href: "#", description: "Acces machine et documentation." },
        ],
      },
      {
        title: "Methodologie",
        links: [
          { label: "Perimetre", href: "#", description: "Champ de collecte et definitions." },
          { label: "Qualite et revisions", href: "#", description: "Processus de controle et versioning." },
          { label: "Licence d'usage", href: "#", description: "Conditions d'utilisation des donnees." },
        ],
      },
    ],
  },
  {
    label: "Projet",
    href: "/project",
    description: "Presentation OCR / reconnaissance de plaques et architecture.",
  },
  {
    label: "Tests",
    columns: [
      {
        title: "Modules reels",
        links: [
          { label: "Hub de demonstration", href: "/tests", description: "Vue d'ensemble des pages de test applicatives." },
          { label: "OCR Documents", href: "/tests/ocr", description: "Upload, liste, structuration et chat document." },
          { label: "MLPDR Plaques", href: "/tests/mlpdr", description: "Detection et lecture de plaques via l'API MLPDR." },
        ],
      },
      {
        title: "Raccourcis",
        links: [
          { label: "Page projet", href: "/project", description: "Presentation fonctionnelle et architecture." },
          { label: "Accueil", href: "/", description: "Retour au portail institutionnel." },
          { label: "Statuts API", href: "/tests", description: "Verifier OCR, MLPDR et points d'acces utiles." },
        ],
      },
    ],
  },
  {
    label: "Contact",
    columns: [
      {
        title: "Nous joindre",
        links: [
          { label: "Contacts institutionnels", href: "#", description: "Points de contact par service." },
          { label: "Media & presse", href: "#", description: "Demandes d'information et kit media." },
          { label: "Localisation", href: "#", description: "Siege, acces et horaires." },
        ],
      },
    ],
  },
];
