/**
 * Générateur pseudo-aléatoire déterministe : les données simulées restent
 * identiques d'un rechargement à l'autre, ce qui rend les dashboards comparables.
 */
export function creerRng(graine: number) {
  let etat = graine >>> 0;
  return () => {
    etat = etat * 1664525 + 1013904223 >>> 0;
    return etat / 4294967296;
  };
}

export function entreBornes(rng: () => number, min: number, max: number): number {
  return Math.round(min + rng() * (max - min));
}

export function choisir<T>(rng: () => number, liste: T[]): T {
  return liste[Math.floor(rng() * liste.length) % liste.length];
}

export const MOIS_DISPONIBLES = ['2026-05', '2026-06', '2026-07', '2026-08'];
export const MOIS_COURANT = '2026-08';

export const DATES_QR = ['2026-06-30', '2026-07-31', '2026-08-26'];
export const DATE_QR_COURANTE = '2026-08-26';

export function joursDuMois(mois: string): string[] {
  const [annee, m] = mois.split('-').map(Number);
  const nb = new Date(Date.UTC(annee, m, 0)).getUTCDate();
  return Array.from(
    { length: nb },
    (_, i) => `${mois}-${String(i + 1).padStart(2, '0')}`
  );
}

export function estWeekend(date: string): boolean {
  return [0].includes(new Date(`${date}T00:00:00Z`).getUTCDay());
}