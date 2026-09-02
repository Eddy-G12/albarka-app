import React, { useState } from 'react';
import { ChevronDownIcon } from 'lucide-react';
import { Section, TitreBloc } from '../ui/Section';
import { BlocAsync, Squelette } from '../ui/States';
import { GrilleMetriques, MetricCard } from '../MetricCard';
import { BarresEmpilees } from '../charts/Charts';
import { DataTable } from '../DataTable';
import { StatusBadge } from '../StatusBadge';
import { useAsync } from '../../hooks/useAsync';
import { getAgentsPrioritaires, getQrParDsm, getQrParSegment, getRepartitionQr } from '../../services/qr';
import { COULEUR_STATUT, LIBELLE_STATUT } from '../../utils/business';
import { formatNombre, formatPourcent, labelDate } from '../../utils/format';

const SERIES_STATUT = [
{ cle: 'sans_qr', nom: LIBELLE_STATUT.sans_qr, couleur: COULEUR_STATUT.sans_qr },
{ cle: 'non_utilise', nom: LIBELLE_STATUT.non_utilise, couleur: COULEUR_STATUT.non_utilise },
{ cle: 'risque', nom: LIBELLE_STATUT.risque, couleur: COULEUR_STATUT.risque },
{ cle: 'actif', nom: LIBELLE_STATUT.actif, couleur: COULEUR_STATUT.actif }];


export function SectionQr({
  dateRef,
  dsmName,
  avecDsm = true




}: {dateRef: string;dsmName?: string;avecDsm?: boolean;}) {
  const [prioritairesOuverts, setPrioritairesOuverts] = useState(false);
  const repartition = useAsync(() => getRepartitionQr(dateRef, dsmName), [dateRef, dsmName]);
  const parSegment = useAsync(() => getQrParSegment(dateRef, dsmName), [dateRef, dsmName]);
  const parDsm = useAsync(() => getQrParDsm(dateRef), [dateRef]);
  const prioritaires = useAsync(() => getAgentsPrioritaires(dateRef, dsmName), [dateRef, dsmName]);

  return (
    <Section
      id="qr"
      titre="QR Code"
      description={`Classification des agents terrain au ${labelDate(dateRef)}.`}>
      
      <div className="space-y-6">
        <BlocAsync etat={repartition} squelette={<Squelette lignes={3} hauteur="h-16" />}>
          {({ repartition: r }) =>
          <>
              <GrilleMetriques colonnes={5}>
                <MetricCard libelle="Total agents" valeur={formatNombre(r.total)} principale />
                <MetricCard libelle="Sans QR Code" valeur={formatNombre(r.parStatut.sans_qr)} />
                <MetricCard
                libelle="QR non utilisé (+30j)"
                valeur={formatNombre(r.parStatut.non_utilise)} />
              
                <MetricCard libelle="Risque inactivité" valeur={formatNombre(r.parStatut.risque)} />
                <MetricCard libelle="Agents actifs" valeur={formatNombre(r.parStatut.actif)} />
              </GrilleMetriques>

              <div className="mt-3">
                <GrilleMetriques colonnes={5}>
                  <MetricCard libelle="Taux déploiement" valeur={formatPourcent(r.tauxDeploiement)} />
                  <MetricCard libelle="Taux utilisation" valeur={formatPourcent(r.tauxUtilisation)} />
                  <MetricCard libelle="QR non utilisés" valeur={formatPourcent(r.tauxNonUtilises)} />
                  <MetricCard libelle="Risque" valeur={formatPourcent(r.tauxRisque)} />
                  <MetricCard libelle="Sans QR" valeur={formatPourcent(r.tauxSansQr)} />
                </GrilleMetriques>
              </div>
            </>
          }
        </BlocAsync>

        <div>
          <TitreBloc>Répartition par segment</TitreBloc>
          <BlocAsync etat={parSegment} squelette={<Squelette lignes={5} />}>
            {(segments) =>
            <BarresEmpilees donnees={segments} cleLabel="segment" series={SERIES_STATUT} />
            }
          </BlocAsync>
        </div>

        {avecDsm &&
        <div>
            <TitreBloc>Classement DSM par agents actifs</TitreBloc>
            <BlocAsync etat={parDsm} squelette={<Squelette lignes={5} />}>
              {(lignes) =>
            <DataTable
              colonnes={[
              { cle: 'dsmName', entete: 'DSM' },
              { cle: 'total', entete: 'Agents', numerique: true },
              { cle: 'actif', entete: 'Actifs', numerique: true },
              { cle: 'risque', entete: 'Risque', numerique: true },
              { cle: 'non_utilise', entete: 'Non utilisés', numerique: true },
              { cle: 'sans_qr', entete: 'Sans QR', numerique: true },
              {
                cle: 'tauxUtilisation',
                entete: 'Taux utilisation',
                numerique: true,
                rendu: (l) => formatPourcent(l.tauxUtilisation)
              }]
              }
              lignes={lignes}
              cleLigne={(l) => l.dsmName}
              parPage={10}
              compact />

            }
            </BlocAsync>
          </div>
        }

        <div className="rounded-md border border-albarka-border">
          <button
            type="button"
            aria-expanded={prioritairesOuverts}
            onClick={() => setPrioritairesOuverts((v) => !v)}
            className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-albarka-black">
            
            Agents prioritaires (statuts non actifs)
            <ChevronDownIcon
              className={`h-4 w-4 transition-transform duration-150 ease-out ${
              prioritairesOuverts ? 'rotate-180' : ''}`
              }
              aria-hidden />
            
          </button>
          {prioritairesOuverts &&
          <div className="border-t border-albarka-border px-4 py-4">
              <BlocAsync etat={prioritaires} squelette={<Squelette lignes={5} />}>
                {(agents) =>
              <DataTable
                colonnes={[
                { cle: 'posName', entete: 'Agent' },
                { cle: 'posMsisdn', entete: 'MSISDN' },
                { cle: 'dsmName', entete: 'DSM' },
                { cle: 'segmentGroup', entete: 'Segment' },
                { cle: 'town', entete: 'Ville' },
                {
                  cle: 'statut',
                  entete: 'Statut',
                  rendu: (a) => <StatusBadge statut={a.statut} />
                }]
                }
                lignes={agents}
                cleLigne={(a) => a.posMsisdn}
                recherche
                parPage={10}
                compact />

              }
              </BlocAsync>
            </div>
          }
        </div>
      </div>
    </Section>);

}