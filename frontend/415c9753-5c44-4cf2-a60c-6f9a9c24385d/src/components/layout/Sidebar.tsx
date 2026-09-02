import React from 'react';
import { NavLink } from 'react-router-dom';
import { twMerge } from 'tailwind-merge';
import { LogOutIcon } from 'lucide-react';
import { Logo } from '../Logo';
import { navigationPourRole } from '../../config/navigation';
import { useAuth } from '../../contexts/AuthContext';

const LIBELLE_ROLE: Record<string, string> = {
  super_admin: 'Super administrateur',
  admin: 'Administrateur',
  commercial: 'Commercial'
};

export function Sidebar({ onNavigation }: {onNavigation?: () => void;}) {
  const { utilisateur, seDeconnecter } = useAuth();
  if (!utilisateur) return null;

  const entrees = navigationPourRole(utilisateur.role);
  const groupes = [...new Set(entrees.map((e) => e.groupe))];

  return (
    <div className="flex h-full flex-col border-r-2 border-albarka-yellow bg-albarka-black">
      <div className="px-5 py-5">
        <Logo sombre />
      </div>

      <nav
        aria-label="Navigation principale"
        className="albarka-scroll flex-1 overflow-y-auto px-3 pb-4">
        
        {groupes.map((groupe) =>
        <div key={groupe} className="mb-5">
            <p className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-white/35">
              {groupe}
            </p>
            <ul className="space-y-0.5">
              {entrees.
            filter((e) => e.groupe === groupe).
            map((entree) =>
            <li key={entree.chemin}>
                    <NavLink
                to={entree.chemin}
                end={entree.chemin === '/'}
                onClick={onNavigation}
                className={({ isActive }) =>
                twMerge(
                  'flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors duration-150 ease-out',
                  isActive ?
                  'bg-albarka-yellow font-semibold text-albarka-black' :
                  'text-white/75 hover:bg-white/10 hover:text-white'
                )
                }>
                
                      <entree.icone className="h-4 w-4 shrink-0" aria-hidden />
                      <span className="truncate">{entree.libelle}</span>
                    </NavLink>
                  </li>
            )}
            </ul>
          </div>
        )}
      </nav>

      <div className="border-t border-white/10 px-4 py-4">
        <p className="truncate text-sm font-medium text-white">{utilisateur.nom}</p>
        <p className="text-2xs text-white/50">
          {LIBELLE_ROLE[utilisateur.role]}
          {utilisateur.dsmName ? ` · ${utilisateur.dsmName}` : ''}
        </p>
        <button
          type="button"
          onClick={seDeconnecter}
          className="mt-3 inline-flex items-center gap-2 rounded-md border border-white/15 px-2.5 py-1.5 text-xs text-white/75 transition-colors duration-150 ease-out hover:border-white/35 hover:text-white">
          
          <LogOutIcon className="h-3.5 w-3.5" aria-hidden />
          Se déconnecter
        </button>
      </div>
    </div>);

}