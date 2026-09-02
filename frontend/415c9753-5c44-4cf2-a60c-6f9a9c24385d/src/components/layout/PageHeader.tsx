import React from 'react';

export function PageHeader({
  titre,
  description,
  filtres,
  actions





}: {titre: string;description?: string;filtres?: React.ReactNode;actions?: React.ReactNode;}) {
  return (
    <header className="mb-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-albarka-black">{titre}</h1>
          {description &&
          <p className="mt-1 max-w-3xl text-sm text-albarka-muted">{description}</p>
          }
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {filtres &&
      <div className="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-albarka-border bg-white px-4 py-3 shadow-card">
          {filtres}
        </div>
      }
    </header>);

}