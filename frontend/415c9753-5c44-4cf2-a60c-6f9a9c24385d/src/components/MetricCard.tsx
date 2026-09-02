import React from 'react';
import { twMerge } from 'tailwind-merge';
import { ArrowDownRightIcon, ArrowUpRightIcon, MinusIcon } from 'lucide-react';

interface MetricCardProps {
  libelle: string;
  valeur: string;
  unite?: string;
  detail?: string;
  delta?: number;
  deltaLabel?: string;
  principale?: boolean;
  className?: string;
}

export function MetricCard({
  libelle,
  valeur,
  unite,
  detail,
  delta,
  deltaLabel,
  principale = false,
  className
}: MetricCardProps) {
  const sens = delta === undefined ? null : delta > 0 ? 'hausse' : delta < 0 ? 'baisse' : 'stable';
  const Icone =
  sens === 'hausse' ? ArrowUpRightIcon : sens === 'baisse' ? ArrowDownRightIcon : MinusIcon;

  return (
    <div
      className={twMerge(
        'rounded-lg border bg-white px-4 py-3.5 shadow-card',
        principale ?
        'border-albarka-yellow/60 bg-albarka-yellow-soft' :
        'border-albarka-border',
        className
      )}>
      
      <p className="text-2xs font-semibold uppercase tracking-wide text-albarka-muted">
        {libelle}
      </p>
      <p
        className={twMerge(
          'num mt-1.5 font-semibold text-albarka-black',
          principale ? 'text-3xl' : 'text-2xl'
        )}>
        
        {valeur}
        {unite && <span className="ml-1 text-sm font-medium text-albarka-muted">{unite}</span>}
      </p>
      {(detail || sens) &&
      <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
          {sens &&
        <span
          className={twMerge(
            'inline-flex items-center gap-1 font-medium',
            sens === 'hausse' ?
            'text-statut-actif' :
            sens === 'baisse' ?
            'text-[#C0392B]' :
            'text-albarka-muted'
          )}>
          
              <Icone className="h-3.5 w-3.5" aria-hidden />
              {deltaLabel}
            </span>
        }
          {detail && <span className="text-albarka-muted">{detail}</span>}
        </div>
      }
    </div>);

}

export function GrilleMetriques({
  children,
  colonnes = 3



}: {children: React.ReactNode;colonnes?: 2 | 3 | 4 | 5 | 6;}) {
  const classes: Record<number, string> = {
    2: 'sm:grid-cols-2',
    3: 'sm:grid-cols-2 xl:grid-cols-3',
    4: 'sm:grid-cols-2 xl:grid-cols-4',
    5: 'sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5',
    6: 'sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6'
  };
  return <div className={`grid gap-3 ${classes[colonnes]}`}>{children}</div>;
}