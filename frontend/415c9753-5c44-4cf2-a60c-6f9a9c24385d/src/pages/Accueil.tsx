import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRightIcon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { navigationPourRole } from '../config/navigation';
import { useAuth } from '../contexts/AuthContext';

const CONSIGNE_ROLE: Record<string, string> = {
  super_admin:
  'Vous disposez des droits complets : dépôt de fichiers, saisie manuelle, administration des comptes et des seuils.',
  admin:
  'Votre accès est en consultation et export. Les écrans de dépôt et de saisie ne vous sont pas proposés.',
  commercial:
  'Vos écrans sont filtrés sur votre périmètre. Les chiffres des autres commerciaux restent anonymisés.'
};

export function Accueil() {
  const { utilisateur } = useAuth();
  if (!utilisateur) return null;

  const modules = navigationPourRole(utilisateur.role).filter((e) => e.chemin !== '/');
  const groupes = [...new Set(modules.map((m) => m.groupe))];

  return (
    <div>
      <PageHeader
        titre={`Bonjour ${utilisateur.nom.split(' ')[0]}`}
        description={CONSIGNE_ROLE[utilisateur.role]} />
      

      <div className="space-y-7">
        {groupes.map((groupe) =>
        <section key={groupe}>
            <h2 className="mb-3 text-2xs font-semibold uppercase tracking-wide text-albarka-muted">
              {groupe}
            </h2>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {modules.
            filter((m) => m.groupe === groupe).
            map((module) =>
            <Link
              key={module.chemin}
              to={module.chemin}
              className="group flex h-full flex-col rounded-lg border border-albarka-border bg-white p-4 shadow-card transition-colors duration-150 ease-out hover:border-albarka-yellow">
              
                    <div className="flex items-center gap-2.5">
                      <span className="rounded-md bg-albarka-yellow-soft p-1.5">
                        <module.icone className="h-4 w-4 text-[#8A5A05]" aria-hidden />
                      </span>
                      <h3 className="text-sm font-semibold text-albarka-black">
                        {module.libelle}
                      </h3>
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-albarka-muted">
                      {module.description}
                    </p>
                    <span className="mt-auto inline-flex items-center gap-1 pt-3 text-2xs font-medium text-albarka-muted transition-colors duration-150 ease-out group-hover:text-albarka-black">
                      Ouvrir
                      <ArrowRightIcon className="h-3 w-3" aria-hidden />
                    </span>
                  </Link>
            )}
            </div>
          </section>
        )}
      </div>
    </div>);

}