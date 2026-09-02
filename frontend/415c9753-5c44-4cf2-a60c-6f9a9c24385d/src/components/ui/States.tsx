import React from 'react';
import { AlertTriangleIcon, InboxIcon, RotateCcwIcon } from 'lucide-react';
import { Button } from './Button';

export function Squelette({ lignes = 4, hauteur = 'h-4' }: {lignes?: number;hauteur?: string;}) {
  return (
    <div className="space-y-2" role="status" aria-label="Chargement en cours">
      {Array.from({ length: lignes }).map((_, i) =>
      <div
        key={i}
        className={`animate-pulse rounded bg-albarka-bg ${hauteur}`}
        style={{ width: `${100 - i * 7}%` }} />

      )}
    </div>);

}

export function SqueletteCartes({ nb = 4 }: {nb?: number;}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: nb }).map((_, i) =>
      <div
        key={i}
        className="h-24 animate-pulse rounded-lg border border-albarka-border bg-albarka-bg" />

      )}
    </div>);

}

export function EtatVide({
  titre,
  message,
  action




}: {titre: string;message: string;action?: React.ReactNode;}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-albarka-border bg-albarka-bg/60 px-6 py-10 text-center">
      <InboxIcon className="mb-3 h-6 w-6 text-albarka-muted" aria-hidden />
      <p className="text-sm font-semibold text-albarka-black">{titre}</p>
      <p className="mt-1 max-w-md text-xs text-albarka-muted">{message}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>);

}

export function EtatErreur({ message, onReessayer }: {message: string;onReessayer?: () => void;}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-md border border-[#F0C8C4] bg-[#FDF3F2] px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      
      <div className="flex items-start gap-2">
        <AlertTriangleIcon className="mt-0.5 h-4 w-4 shrink-0 text-[#C0392B]" aria-hidden />
        <p className="text-xs text-[#8E2B22]">{message}</p>
      </div>
      {onReessayer &&
      <Button taille="sm" icone={<RotateCcwIcon className="h-3.5 w-3.5" />} onClick={onReessayer}>
          Réessayer
        </Button>
      }
    </div>);

}

/** Enveloppe standard : chargement -> erreur -> contenu. */
export function BlocAsync<T>({
  etat,
  squelette,
  children




}: {etat: {donnees: T | null;chargement: boolean;erreur: string | null;recharger: () => void;};squelette?: React.ReactNode;children: (donnees: T) => React.ReactNode;}) {
  if (etat.chargement && etat.donnees === null) {
    return <>{squelette ?? <Squelette />}</>;
  }
  if (etat.erreur) {
    return <EtatErreur message={etat.erreur} onReessayer={etat.recharger} />;
  }
  if (etat.donnees === null) return null;
  return <>{children(etat.donnees)}</>;
}