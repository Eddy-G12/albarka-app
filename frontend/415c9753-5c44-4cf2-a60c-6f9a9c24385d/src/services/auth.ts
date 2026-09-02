/**
 * src/services/auth.ts
 * =====================
 * Remplace le mock : appelle POST /auth/login sur l'API FastAPI.
 * La session (token + profil) est persistée dans sessionStorage.
 */

import { api, ApiError } from './api';
import type { Utilisateur } from '../types';

export interface ResultatConnexion {
  utilisateur: Utilisateur;
  token: string;
}

export class ErreurConnexion extends Error {}

// ── Connexion ─────────────────────────────────────────────────────────────────

export async function connexion(
  username: string,
  motDePasse: string,
): Promise<ResultatConnexion> {
  try {
    const data = await api.post<{ utilisateur: RawUtilisateur; token: string }>(
      '/auth/login',
      { username, mot_de_passe: motDePasse },
    );
    return {
      utilisateur: mapUtilisateur(data.utilisateur),
      token: data.token,
    };
  } catch (err) {
    if (err instanceof ApiError) {
      throw new ErreurConnexion(err.message);
    }
    throw new ErreurConnexion('Connexion impossible pour le moment.');
  }
}

// ── Profil courant ─────────────────────────────────────────────────────────────

export async function getMe(): Promise<Utilisateur> {
  const data = await api.get<RawUtilisateur>('/auth/me');
  return mapUtilisateur(data);
}

// ── Session ───────────────────────────────────────────────────────────────────

const CLE_SESSION = 'albarka.session';

export function sauverSession(resultat: ResultatConnexion): void {
  try {
    window.sessionStorage.setItem(CLE_SESSION, JSON.stringify(resultat));
  } catch { /* stockage indisponible */ }
}

export function lireSession(): ResultatConnexion | null {
  try {
    const brut = window.sessionStorage.getItem(CLE_SESSION);
    return brut ? JSON.parse(brut) as ResultatConnexion : null;
  } catch {
    return null;
  }
}

export function effacerSession(): void {
  try {
    window.sessionStorage.removeItem(CLE_SESSION);
  } catch { /* rien */ }
}

// ── Mapping snake_case API → camelCase frontend ────────────────────────────────

interface RawUtilisateur {
  id: number;
  username: string;
  nom: string;
  role: 'super_admin' | 'admin' | 'commercial';
  actif: boolean;
  dsm_name?: string | null;
  created_at?: string | null;
}

function mapUtilisateur(raw: RawUtilisateur): Utilisateur {
  return {
    id:         raw.id,
    username:   raw.username,
    nom:        raw.nom,
    role:       raw.role,
    actif:      raw.actif,
    dsmName:    raw.dsm_name ?? undefined,
    createdAt:  raw.created_at ?? '',
  };
}
