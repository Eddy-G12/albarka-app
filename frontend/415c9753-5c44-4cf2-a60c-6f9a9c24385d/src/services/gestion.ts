/**
 * src/services/gestion.ts
 * ========================
 * Remplace le mock : appelle les endpoints /gestion/* de l'API FastAPI.
 */

import { api, qs } from './api';
import type { Parrainage, Role, SuiviPersonne } from '../types';

// ── Historique des imports ─────────────────────────────────────────────────────

export async function getImports(filtres: {
  type?: string;
  recherche?: string;
  limite?: number;
  offset?: number;
}) {
  const data = await api.get<{
    id: number;
    type_fichier: string;
    cle: string;
    date_donnees: string | null;
    chemin_fichier: string;
    nb_lignes: number | null;
    date_execution: string;
    fichier_disponible: boolean;
  }[]>(`/gestion/imports${qs({
    type_fichier: filtres.type === 'tous' ? undefined : filtres.type,
    recherche:    filtres.recherche,
    limite:       filtres.limite ?? 5,
    offset:       filtres.offset ?? 0,
  })}`);

  return data.map(r => ({
    id:               r.id,
    typeFichier:      r.type_fichier,
    cle:              r.cle,
    dateDonnees:      r.date_donnees,
    cheminFichier:    r.chemin_fichier,
    nbLignes:         r.nb_lignes,
    dateExecution:    r.date_execution,
    fichierDisponible: r.fichier_disponible,
  }));
}

export async function getTotalImports(type?: string): Promise<number> {
  const data = await api.get<{ total: number }>(
    `/gestion/imports/total${qs({ type_fichier: type === 'tous' ? undefined : type })}`,
  );
  return data.total;
}

/** Supprime uniquement l'enregistrement en base — JAMAIS le fichier sur disque. */
export async function supprimerImport(id: number): Promise<void> {
  await api.del(`/gestion/imports/${id}`);
}

/** URL de téléchargement direct du fichier Excel généré. */
export function urlTelechargement(id: number): string {
  const base = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '')
    ?? 'http://localhost:8000';
  return `${base}/gestion/imports/${id}/download`;
}

// ── Parrainages ────────────────────────────────────────────────────────────────

export async function getParrainages(du?: string, au?: string) {
  const data = await api.get<{
    lignes: { personne: string; date_op: string; nb: number }[];
    synthese: { personne: string; total: number }[];
    total: number;
  }>(`/gestion/parrainages${qs({ du, au })}`);

  return {
    lignes:   data.lignes.map(r => ({ personne: r.personne, dateOp: r.date_op, nb: r.nb })),
    synthese: data.synthese,
    total:    data.total,
  };
}

export async function enregistrerParrainage(entree: Parrainage): Promise<void> {
  await api.post('/gestion/parrainages', {
    personne: entree.personne,
    date_op:  entree.dateOp,
    nb:       entree.nb,
  });
}

export async function supprimerParrainage(personne: string, dateOp: string): Promise<void> {
  await api.del(`/gestion/parrainages/${encodeURIComponent(personne)}/${dateOp}`);
}

// ── Suivi personnes ────────────────────────────────────────────────────────────

export async function getSuiviPersonnes(filtres: {
  commercialId?: number;
  du?: string;
  au?: string;
}) {
  const data = await api.get<{
    lignes: {
      id: number;
      commercial_id: number;
      dsm_name: string;
      nom_personne: string;
      montant: number;
      date_heure: string;
    }[];
    synthese: {
      dsm_name: string;
      nom_personne: string;
      montant: number;
      nb_entrees: number;
    }[];
    montant_total: number;
    personnes_distinctes: number;
  }>(`/gestion/suivi-personnes${qs({
    commercial_id: filtres.commercialId,
    du:            filtres.du,
    au:            filtres.au,
  })}`);

  return {
    lignes: data.lignes.map(r => ({
      id:           r.id,
      commercialId: r.commercial_id,
      dsmName:      r.dsm_name,
      nomPersonne:  r.nom_personne,
      montant:      r.montant,
      dateHeure:    r.date_heure,
    })),
    synthese: data.synthese.map(r => ({
      dsmName:     r.dsm_name,
      nomPersonne: r.nom_personne,
      montant:     r.montant,
      nbEntrees:   r.nb_entrees,
    })),
    montantTotal:        data.montant_total,
    personnesDistinctes: data.personnes_distinctes,
  };
}

export async function enregistrerSuivi(
  entree: Omit<SuiviPersonne, 'id'>,
): Promise<void> {
  await api.post('/gestion/suivi-personnes', {
    commercial_id: entree.commercialId,
    nom_personne:  entree.nomPersonne,
    montant:       entree.montant,
    date_heure:    entree.dateHeure,
  });
}

export async function supprimerSuivi(id: number): Promise<void> {
  await api.del(`/gestion/suivi-personnes/${id}`);
}

// ── Administration : utilisateurs ─────────────────────────────────────────────

export async function getUtilisateurs() {
  const data = await api.get<{
    id: number;
    username: string;
    nom: string;
    role: Role;
    actif: boolean;
    dsm_name: string | null;
    created_at: string | null;
  }[]>('/gestion/utilisateurs');

  return data.map(r => ({
    id:        r.id,
    username:  r.username,
    nom:       r.nom,
    role:      r.role,
    actif:     r.actif,
    dsmName:   r.dsm_name ?? undefined,
    createdAt: r.created_at ?? '',
  }));
}

export async function creerUtilisateur(entree: {
  username: string;
  nom: string;
  role: Role;
  dsmName?: string;
  motDePasse?: string;
}) {
  return api.post('/gestion/utilisateurs', {
    username:    entree.username,
    nom:         entree.nom,
    role:        entree.role,
    mot_de_passe: entree.motDePasse ?? `${entree.username}123`,
    dsm_name:    entree.dsmName,
  });
}

export async function majUtilisateur(
  id: number,
  champs: { nom?: string; actif?: boolean },
): Promise<void> {
  await api.patch(`/gestion/utilisateurs/${id}`, champs);
}

// ── Administration : commerciaux ──────────────────────────────────────────────

export async function getCommerciaux() {
  const data = await api.get<{
    id: number;
    utilisateur_id: number | null;
    dsm_name: string;
    telephone: string | null;
    zone: string | null;
    actif: boolean;
    alias: string | null;
  }[]>('/gestion/commerciaux');

  return data.map(r => ({
    id:           r.id,
    utilisateurId: r.utilisateur_id ?? 0,
    dsmName:      r.dsm_name,
    telephone:    r.telephone ?? '',
    zone:         r.zone ?? '',
    actif:        r.actif,
    alias:        r.alias,
  }));
}

export async function majCommercial(
  id: number,
  champs: {
    telephone?: string;
    zone?: string;
    dsmName?: string;
    actif?: boolean;
    alias?: string | null;
  },
): Promise<void> {
  await api.patch(`/gestion/commerciaux/${id}`, {
    telephone: champs.telephone,
    zone:      champs.zone,
    dsm_name:  champs.dsmName,
    actif:     champs.actif,
    alias:     champs.alias,
  });
}

// ── Administration : seuils ───────────────────────────────────────────────────

export async function getSeuils() {
  const data = await api.get<{
    id: number;
    type_flux: 'cash_in' | 'cash_out';
    valeur: number;
    mois: string | null;
    created_by: string | null;
    created_at: string | null;
  }[]>('/gestion/seuils');

  return data.map(r => ({
    id:        r.id,
    typeFlux:  r.type_flux,
    valeur:    r.valeur,
    mois:      r.mois,
    createdBy: r.created_by ?? '',
    createdAt: r.created_at ?? '',
  }));
}

export async function enregistrerSeuil(entree: {
  typeFlux: 'cash_in' | 'cash_out';
  valeur: number;
  mois: string | null;
  createdBy: string;
}): Promise<void> {
  await api.post('/gestion/seuils', {
    type_flux: entree.typeFlux,
    valeur:    entree.valeur,
    mois:      entree.mois,
  });
}
