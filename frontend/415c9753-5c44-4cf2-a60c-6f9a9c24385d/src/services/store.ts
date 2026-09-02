/**
 * src/services/store.ts
 * ======================
 * Le store mock (données en mémoire) est remplacé par l'API FastAPI.
 *
 * Ce fichier est conservé uniquement pour la compatibilité avec les
 * quelques endroits qui l'importent encore (ex. AuthContext).
 * Il ne contient plus de données initiales — tout vient de l'API.
 *
 * Les fonctions delai() et prochainId() restent disponibles au cas où
 * un composant les utilise directement.
 */

import type { Commercial } from '../types';

/**
 * Store résiduel minimal.
 * `commerciaux` est peuplé par AuthContext depuis /gestion/commerciaux
 * afin de résoudre le commercial lié à l'utilisateur connecté.
 */
export const store: { commerciaux: Commercial[] } = {
  commerciaux: [],
};

/** Conservé pour compatibilité — simule un délai réseau si nécessaire. */
export function delai<T>(valeur: T, ms = 0): Promise<T> {
  if (ms <= 0) return Promise.resolve(valeur);
  return new Promise((resolve) => setTimeout(() => resolve(valeur), ms));
}

/** Conservé pour compatibilité. */
export function prochainId(liste: { id: number }[]): number {
  return liste.reduce((max, item) => Math.max(max, item.id), 0) + 1;
}
