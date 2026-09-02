const MOIS_LABELS = [
'janvier',
'février',
'mars',
'avril',
'mai',
'juin',
'juillet',
'août',
'septembre',
'octobre',
'novembre',
'décembre'];


export function formatFcfa(value: number, compact = false): string {
  if (!Number.isFinite(value)) return '—';
  const abs = Math.abs(value);
  if (compact && abs >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} M`;
  }
  if (compact && abs >= 10_000) {
    return `${(value / 1_000).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} k`;
  }
  return value.toLocaleString('fr-FR', { maximumFractionDigits: 0 });
}

export function formatNombre(value: number): string {
  if (!Number.isFinite(value)) return '—';
  return value.toLocaleString('fr-FR', { maximumFractionDigits: 1 });
}

export function formatPourcent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return '—';
  return `${value.toLocaleString('fr-FR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  })} %`;
}

export function formatDelta(value: number): string {
  const signe = value > 0 ? '+' : '';
  return `${signe}${formatFcfa(value, true)}`;
}

/** '2026-04' -> 'avril 2026' */
export function labelMois(mois: string): string {
  const [annee, m] = mois.split('-');
  const index = Number(m) - 1;
  if (!MOIS_LABELS[index]) return mois;
  return `${MOIS_LABELS[index]} ${annee}`;
}

/** '2026-04-08' -> '08/04/2026' */
export function labelDate(date: string): string {
  const [a, m, j] = date.split('-');
  if (!j) return date;
  return `${j}/${m}/${a}`;
}

export function labelDateHeure(valeur: string): string {
  const [date, heure = ''] = valeur.split(' ');
  return `${labelDate(date)} ${heure.slice(0, 5)}`.trim();
}

/** '2026-04' -> '2026-03' */
export function moisPrecedent(mois: string): string {
  const [annee, m] = mois.split('-').map(Number);
  const date = new Date(Date.UTC(annee, m - 2, 1));
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
}

export function moisDeDate(date: string): string {
  return date.slice(0, 7);
}

export function evolutionPct(actuel: number, precedent: number): number {
  if (!precedent) return actuel ? 100 : 0;
  return (actuel - precedent) / Math.abs(precedent) * 100;
}

export function formatMinutes(minutes: number | null): string {
  if (minutes === null || !Number.isFinite(minutes)) return 'N/A';
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return m ? `${h} h ${m}` : `${h} h`;
}