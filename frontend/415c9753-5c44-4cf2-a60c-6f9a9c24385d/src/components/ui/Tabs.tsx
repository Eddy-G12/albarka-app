import React, { useState } from 'react';
import { twMerge } from 'tailwind-merge';

export interface Onglet {
  id: string;
  libelle: string;
  contenu: React.ReactNode;
}

export function Tabs({
  onglets,
  defaut,
  className




}: {onglets: Onglet[];defaut?: string;className?: string;}) {
  const [actif, setActif] = useState(defaut ?? onglets[0]?.id);
  const courant = onglets.find((o) => o.id === actif) ?? onglets[0];

  return (
    <div className={className}>
      <div
        role="tablist"
        aria-label="Sections de la page"
        className="mb-4 flex flex-wrap items-center gap-1 border-b border-albarka-border">
        
        {onglets.map((onglet) => {
          const estActif = onglet.id === courant?.id;
          return (
            <button
              key={onglet.id}
              role="tab"
              type="button"
              aria-selected={estActif}
              onClick={() => setActif(onglet.id)}
              className={twMerge(
                '-mb-px border-b-2 px-3 py-2 text-sm transition-colors duration-150 ease-out',
                estActif ?
                'border-albarka-yellow font-semibold text-albarka-black' :
                'border-transparent text-albarka-muted hover:text-albarka-black'
              )}>
              
              {onglet.libelle}
            </button>);

        })}
      </div>
      <div role="tabpanel">{courant?.contenu}</div>
    </div>);

}