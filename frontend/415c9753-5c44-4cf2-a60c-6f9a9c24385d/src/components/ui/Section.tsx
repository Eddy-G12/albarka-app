import React from 'react';
import { twMerge } from 'tailwind-merge';

export function Section({
  titre,
  description,
  actions,
  children,
  className,
  id







}: {titre?: string;description?: string;actions?: React.ReactNode;children: React.ReactNode;className?: string;id?: string;}) {
  return (
    <section
      id={id}
      className={twMerge(
        'rounded-lg border border-albarka-border bg-white shadow-card',
        className
      )}>
      
      {(titre || actions) &&
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-albarka-border px-5 py-4">
          <div>
            {titre && <h2 className="text-sm font-semibold text-albarka-black">{titre}</h2>}
            {description &&
          <p className="mt-0.5 max-w-2xl text-xs text-albarka-muted">{description}</p>
          }
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      }
      <div className="px-5 py-4">{children}</div>
    </section>);

}

export function TitreBloc({ children }: {children: React.ReactNode;}) {
  return (
    <h3 className="mb-3 text-2xs font-semibold uppercase tracking-wide text-albarka-muted">
      {children}
    </h3>);

}