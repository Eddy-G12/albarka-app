import type { QrStatut, RangAnonymise } from '../types';

/**
 * Classification QR Code — ordre de priorité strict, à ne jamais réordonner.
 * 1. active_deployed vide/nul        -> Sans QR Code
 * 2. active_30 == 0                  -> QR non utilisé (+30j)
 * 3. date_ref - last_qr_co_date >=20 -> Risque inactivité
 * 4. sinon                           -> Actif
 */
export function classerAgentQr(params: {
  activeDeployed: number | null | undefined;
  active30: number;
  lastQrCoDate: string | null;
  dateRef: string;
}): QrStatut {
  const { activeDeployed, active30, lastQrCoDate, dateRef } = params;
  if (activeDeployed === null || activeDeployed === undefined || activeDeployed === 0) {
    return 'sans_qr';
  }
  if (active30 === 0) return 'non_utilise';
  if (lastQrCoDate) {
    const ecart = joursEntre(lastQrCoDate, dateRef);
    if (ecart >= 20) return 'risque';
  }
  return 'actif';
}

export const LIBELLE_STATUT: Record<QrStatut, string> = {
  actif: 'Actif',
  risque: 'Risque inactivité',
  non_utilise: 'QR non utilisé (+30j)',
  sans_qr: 'Sans QR Code'
};

export const COULEUR_STATUT: Record<QrStatut, string> = {
  actif: '#1E9E62',
  risque: '#F5A623',
  non_utilise: '#E8702A',
  sans_qr: '#D0342C'
};

export const ORDRE_STATUTS: QrStatut[] = ['sans_qr', 'non_utilise', 'risque', 'actif'];

export function joursEntre(debut: string, fin: string): number {
  const d = Date.parse(`${debut}T00:00:00Z`);
  const f = Date.parse(`${fin}T00:00:00Z`);
  if (Number.isNaN(d) || Number.isNaN(f)) return 0;
  return Math.round((f - d) / 86_400_000);
}

/** Extraction du MSISDN depuis une colonne From/To du CSV brut MTN. */
export function extraireMsisdn(valeur: string): string | null {
  const match = /FRI:(\d{9,12})\/MSISDN/.exec(valeur);
  return match ? match[1] : null;
}

/** Médiane d'une série (null si série vide). */
export function mediane(valeurs: number[]): number | null {
  if (!valeurs.length) return null;
  const tri = [...valeurs].sort((a, b) => a - b);
  const milieu = Math.floor(tri.length / 2);
  return tri.length % 2 ? tri[milieu] : (tri[milieu - 1] + tri[milieu]) / 2;
}

/** Écarts en minutes entre transactions consécutives d'une même journée. */
export function tempsMorts(horodatagesParJour: Record<string, string[]>): number[] {
  const ecarts: number[] = [];
  Object.values(horodatagesParJour).forEach((liste) => {
    const tri = [...liste].sort();
    for (let i = 1; i < tri.length; i += 1) {
      const delta = (Date.parse(tri[i]) - Date.parse(tri[i - 1])) / 60_000;
      if (Number.isFinite(delta) && delta >= 0) ecarts.push(delta);
    }
  });
  return ecarts;
}

export const SEUIL_FLOTTE_BASSE = 100_000;

/**
 * Temps de recharge : durée entre le passage du solde sous 100 000 FCFA
 * et le premier retour au-dessus du seuil.
 */
export function tempsRecharge(
operations: {horodatage: string;balance: number;}[])
: number[] {
  const durees: number[] = [];
  let debutBasse: string | null = null;
  operations.
  slice().
  sort((a, b) => a.horodatage.localeCompare(b.horodatage)).
  forEach((op) => {
    if (op.balance < SEUIL_FLOTTE_BASSE) {
      if (debutBasse === null) debutBasse = op.horodatage;
    } else if (debutBasse !== null) {
      const delta = (Date.parse(op.horodatage) - Date.parse(debutBasse)) / 60_000;
      if (Number.isFinite(delta) && delta >= 0) durees.push(delta);
      debutBasse = null;
    }
  });
  return durees;
}

/**
 * Classement cash anonymisé : le commercial voit son rang réel,
 * les autres deviennent « Commercial #N » et seuls les voisins ±2 sont visibles.
 */
export function classementAnonymise(
classement: {dsmName: string;cashIn: number;cashOut: number;}[],
dsmName: string,
fenetre = 2)
: {lignes: RangAnonymise[];position: number;total: number;} {
  const tri = [...classement].sort((a, b) => b.cashIn - a.cashIn);
  const index = tri.findIndex((l) => l.dsmName === dsmName);
  const lignes = tri.
  map((ligne, i) => ({
    position: i + 1,
    libelle: ligne.dsmName === dsmName ? dsmName : `Commercial #${i + 1}`,
    cashIn: ligne.cashIn,
    cashOut: ligne.cashOut,
    estMoi: ligne.dsmName === dsmName
  })).
  filter((_, i) => index >= 0 && Math.abs(i - index) <= fenetre);
  return { lignes, position: index + 1, total: tri.length };
}

export function somme(valeurs: number[]): number {
  return valeurs.reduce((acc, v) => acc + v, 0);
}