/**
 * src/services/import.ts
 * =======================
 * Appels aux endpoints /import/* de l'API FastAPI.
 * Chaque fonction prend un ou plusieurs fichiers et retourne un résumé JSON.
 */

import { api } from './api';

// ── Types de retour ───────────────────────────────────────────────────────────

export interface ResultatImportTx {
  fichier:           string;
  nb_lignes:         number;
  points_par_jour:   number;
  commercial:        string | null;
  alias:             string | null;
  nb_clients_servis: number;
  appro_ok:          boolean;
  message:           string;
}

export interface ResultatImportQr {
  date_ref:        string;
  nb_agents:       number;
  sans_qr:         number;
  non_utilise:     number;
  risque:          number;
  actif:           number;
  fichier_rapport: string;
  message:         string;
}

export interface ResultatImportSae {
  mois:           string;
  nb_pos:         number;
  total_cash_in:  number;
  total_cash_out: number;
  message:        string;
}

export interface ResultatImportPortefeuille {
  portefeuille_id: number;
  nom:             string;
  commercial:      string;
  nb_clients:      number;
  message:         string;
}

// ── Helper multipart ──────────────────────────────────────────────────────────

function buildUrl(path: string): string {
  const base = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '')
    ?? 'http://localhost:8000';
  return `${base}${path}`;
}

function authHeaders(): Record<string, string> {
  try {
    const raw = sessionStorage.getItem('albarka.session');
    if (!raw) return {};
    const { token } = JSON.parse(raw) as { token: string };
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

async function postFormData<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(buildUrl(path), {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const json = await res.json();
      detail = json.detail ?? detail;
    } catch { /* rien */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ── Endpoints d'import ────────────────────────────────────────────────────────

/**
 * Import CSV Mobile Money (un ou plusieurs fichiers).
 * POST /import/transactions
 */
export async function importerTransactions(
  fichiers: File[],
): Promise<ResultatImportTx[]> {
  const form = new FormData();
  for (const f of fichiers) form.append('fichiers', f);
  return postFormData<ResultatImportTx[]>('/import/transactions', form);
}

/**
 * Import fichier QR Code (.xlsx ou .gz).
 * POST /import/qr
 */
export async function importerQr(
  fichier: File,
  dateRef?: string,
): Promise<ResultatImportQr> {
  const form = new FormData();
  form.append('fichier', fichier);
  if (dateRef) form.append('date_ref', dateRef);
  return postFormData<ResultatImportQr>('/import/qr', form);
}

/**
 * Import fichier SAE MTN (.xlsx ou .csv).
 * POST /import/sae
 */
export async function importerSae(
  fichier: File,
  mois?: string,
): Promise<ResultatImportSae> {
  const form = new FormData();
  form.append('fichier', fichier);
  if (mois) form.append('mois', mois);
  return postFormData<ResultatImportSae>('/import/sae', form);
}

/**
 * Import portefeuille clients (.xlsx).
 * POST /import/portefeuille
 */
export async function importerPortefeuille(
  fichier: File,
  commercialId: number,
  nom: string,
): Promise<ResultatImportPortefeuille> {
  const form = new FormData();
  form.append('fichier', fichier);
  form.append('commercial_id', String(commercialId));
  form.append('nom', nom);
  return postFormData<ResultatImportPortefeuille>('/import/portefeuille', form);
}
