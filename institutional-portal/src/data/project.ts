export const projectOverview = {
  title: "Plateforme OCR & Lecture de Plaques",
  summary:
    "Une plateforme unifiée pour numériser des documents, extraire des données structurées et traiter la reconnaissance de plaques dans un cadre exploitable par les équipes métiers.",
  context:
    "Le projet rassemble plusieurs briques (OCR documentaire, structuration, API d'intégration et module de lecture de plaques) au sein d'une architecture cohérente, avec une interface unique pour la démonstration et l'exploitation.",
};

export const projectFeatures = [
  {
    title: "Extraction OCR multi-format",
    description: "Traitement de PDF et images avec restitution du texte brut et des données normalisées.",
  },
  {
    title: "Structuration assistée",
    description: "Post-traitement des contenus OCR pour obtenir un JSON métier exploitable.",
  },
  {
    title: "Reconnaissance de plaques",
    description: "Module de détection et lecture de plaques avec pipeline dédié et visualisation des étapes.",
  },
  {
    title: "API unifiée",
    description: "Exposition de points d'accès cohérents pour les modules OCR et MLPDR via une même passerelle.",
  },
  {
    title: "Persistance & traçabilité",
    description: "Stockage des documents, résultats et métadonnées pour consultation et contrôle qualité.",
  },
  {
    title: "Déploiement Docker",
    description: "Orchestration des services frontend, backend et base de données pour des tests rapides.",
  },
];

export const workflowSteps = [
  {
    step: "01",
    title: "Ingestion",
    description: "L'utilisateur dépose un document ou une image véhicule via l'interface unifiée.",
  },
  {
    step: "02",
    title: "Traitement IA",
    description: "Les services OCR / MLPDR exécutent extraction, détection, lecture et génération des artefacts.",
  },
  {
    step: "03",
    title: "Structuration",
    description: "Les données sont transformées en format métier (JSON) et prêtes pour validation ou export.",
  },
  {
    step: "04",
    title: "Exploitation",
    description: "Consultation, recherche, suivi qualité et intégration vers d'autres processus applicatifs.",
  },
];

export const techStack = [
  "React",
  "Vite",
  "React Router",
  "TailwindCSS",
  "FastAPI",
  "PostgreSQL",
  "Docker Compose",
  "Nginx",
  "OCR Pipeline",
  "MLPDR / ANPR",
];
