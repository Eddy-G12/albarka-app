import React, { useState } from 'react';
import { ChevronDownIcon } from 'lucide-react';
import { Section, TitreBloc } from '../ui/Section';
import { BlocAsync, Squelette, EtatVide } from '../ui/States';
import { GrilleMetriques, MetricCard } from '../MetricCard';
import { BarresEmpilees } from '../charts/Charts';
import { DataTable } from '../DataTable';
import { StatusBadge } from '../StatusBadge';
import { Tabs } from '../ui/Tabs';
import { useAsync } from '../../hooks/useAsync';
import {
  getAgentsPrioritaires,
  getAgentsQr,
  getQrParDsm,
  getQrParSegment,
  getRepartitionQr,
} from '../../services/qr';
import { COULEUR_STATUT, LIBELLE_STATUT } from '../../utils/business';
import { formatNombre, formatPourcent, labelDate } from '../../utils/format';

// ── Constantes ─────────────────────────────────────────────────────────────────

const SERIES_STATUT = [
  { cle: 'sans_qr',    nom: LIBELLE_STATUT.sans_qr,    couleur: COULEUR_STATUT.sans_qr    },
  { cle: 'non_utilise',nom: LIBELLE_STATUT.non_utilise, couleur: COULEUR_STATUT.non_utilise },
  { cle: 'risque',     nom: LIBELLE_STATUT.risque,      couleur: COULEUR_STATUT.risque      },
  { cle: 'actif',      nom: LIBELLE_STATUT.actif,       couleur: COULEUR_STATUT.actif       },
];

// Valeurs API pour chaque option du sélecteur
const SEGMENTS = [
  { label: 'Tous',            valeur: undefined    },
  { label: 'HVC (Haut)',      valeur: '1-HVC'      },
  { label: 'MVC (Moyen)',     valeur: '2-MVC'      },
  { label: 'LVC (Bas)',       valeur: '3-LVC'      },
] as const;

type SegmentValeur = (typeof SEGMENTS)[number]['valeur'];

// ── Sous-composant : tableau agents d'un segment ───────────────────────────────

function ListeAgentsSegment({
  dateRef,
  dsmName,
  segmentGroup,
}: {
  dateRef: string;
  dsmName?: string;
  segmentGroup: string;
}) {
  const agents = useAsync(
    () => getAgentsQr(dateRef, dsmName, segmentGroup),
    [dateRef, dsmName, segmentGroup],
  );

  return (
    <BlocAsync etat={agents} squelette={<Squelette lignes={6} />}>
      {(liste) =>
        liste.length === 0 ? (
          <EtatVide titre="Aucun agent" message="Aucun agent pour ce segment." />
        ) : (
          <DataTable
            colonnes={[
              { cle: 'posName',      entete: 'Agent'    },
              { cle: 'posMsisdn',    entete: 'MSISDN'   },
              { cle: 'dsmName',      entete: 'DSM'      },
              { cle: 'segmentGroup', entete: 'Segment'  },
              { cle: 'region',       entete: 'Région'   },
              { cle: 'town',         entete: 'Ville'    },
              {
                cle: 'statut',
                entete: 'Statut',
                rendu: (a) => <StatusBadge statut={a.statut} />,
              },
            ]}
            lignes={liste}
            cleLigne={(a) => a.posMsisdn}
            recherche
            parPage={15}
            compact
          />
        )
      }
    </BlocAsync>
  );
}

// ── Composant principal ────────────────────────────────────────────────────────

export function SectionQr({
  dateRef,
  dsmName,
  avecDsm = true,
}: {
  dateRef: string;
  dsmName?: string;
  avecDsm?: boolean;
}) {
  const [segment, setSegment] = useState<SegmentValeur>(undefined);
  const [prioritairesOuverts, setPrioritairesOuverts] = useState(false);

  const repartition = useAsync(
    () => getRepartitionQr(dateRef, dsmName, segment),
    [dateRef, dsmName, segment],
  );
  const parSegment = useAsync(
    () => getQrParSegment(dateRef, dsmName, segment),
    [dateRef, dsmName, segment],
  );
  const parDsm      = useAsync(() => getQrParDsm(dateRef), [dateRef]);
  const prioritaires = useAsync(
    () => getAgentsPrioritaires(dateRef, dsmName, segment),
    [dateRef, dsmName, segment],
  );

  return (
    <Section
      id="qr"
      titre="QR Code"
      description={`Classification des agents terrain au ${labelDate(dateRef)}.`}
      actions={
        /* Sélecteur de segment */
        <div className="flex items-center gap-1 flex-wrap">
          {SEGMENTS.map((s) => (
            <button
              key={String(s.valeur)}
              onClick={() => setSegment(s.valeur)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors border ${
                segment === s.valeur
                  ? 'bg-albarka-black text-white border-albarka-black'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-albarka-black'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      }
    >
      <div className="space-y-6">

        {/* Métriques globales */}
        <BlocAsync etat={repartition} squelette={<Squelette lignes={3} hauteur="h-16" />}>
          {({ repartition: r }) => (
            <>
              <GrilleMetriques colonnes={5}>
                <MetricCard libelle="Total agents"       valeur={formatNombre(r.total)}                 principale />
                <MetricCard libelle="Sans QR Code"       valeur={formatNombre(r.parStatut.sans_qr)}     />
                <MetricCard libelle="QR non utilisé (+30j)" valeur={formatNombre(r.parStatut.non_utilise)} />
                <MetricCard libelle="Risque inactivité"  valeur={formatNombre(r.parStatut.risque)}      />
                <MetricCard libelle="Agents actifs"      valeur={formatNombre(r.parStatut.actif)}       />
              </GrilleMetriques>
              <div className="mt-3">
                <GrilleMetriques colonnes={5}>
                  <MetricCard libelle="Taux déploiement" valeur={formatPourcent(r.tauxDeploiement)} />
                  <MetricCard libelle="Taux utilisation" valeur={formatPourcent(r.tauxUtilisation)} />
                  <MetricCard libelle="QR non utilisés"  valeur={formatPourcent(r.tauxNonUtilises)} />
                  <MetricCard libelle="Risque"           valeur={formatPourcent(r.tauxRisque)}      />
                  <MetricCard libelle="Sans QR"          valeur={formatPourcent(r.tauxSansQr)}      />
                </GrilleMetriques>
              </div>
            </>
          )}
        </BlocAsync>

        {/* Onglets : Graphique / Listes HVC-MVC-LVC */}
        <Tabs
          onglets={[
            {
              id: 'graphique',
              libelle: 'Répartition',
              contenu: (
                <div className="space-y-6 pt-2">
                  <div>
                    <TitreBloc>Répartition par segment</TitreBloc>
                    <BlocAsync etat={parSegment} squelette={<Squelette lignes={5} />}>
                      {(segments) => (
                        <BarresEmpilees
                          donnees={segments}
                          cleLabel="segment"
                          series={SERIES_STATUT}
                          titre={`qr-segments-${dateRef}`}
                        />
                      )}
                    </BlocAsync>
                  </div>

                  {avecDsm && (
                    <div>
                      <TitreBloc>Classement DSM par agents actifs</TitreBloc>
                      <BlocAsync etat={parDsm} squelette={<Squelette lignes={5} />}>
                        {(lignes) => (
                          <DataTable
                            colonnes={[
                              { cle: 'dsmName',          entete: 'DSM'              },
                              { cle: 'total',            entete: 'Agents',     numerique: true },
                              { cle: 'actif',            entete: 'Actifs',     numerique: true },
                              { cle: 'risque',           entete: 'Risque',     numerique: true },
                              { cle: 'non_utilise',      entete: 'Non utilisés', numerique: true },
                              { cle: 'sans_qr',          entete: 'Sans QR',    numerique: true },
                              {
                                cle: 'tauxUtilisation',
                                entete: 'Taux utilisation',
                                numerique: true,
                                rendu: (l) => formatPourcent(l.tauxUtilisation),
                              },
                            ]}
                            lignes={lignes}
                            cleLigne={(l) => l.dsmName}
                            parPage={10}
                            compact
                          />
                        )}
                      </BlocAsync>
                    </div>
                  )}

                  {/* Agents prioritaires */}
                  <div className="rounded-md border border-albarka-border">
                    <button
                      type="button"
                      aria-expanded={prioritairesOuverts}
                      onClick={() => setPrioritairesOuverts((v) => !v)}
                      className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-albarka-black"
                    >
                      Agents prioritaires (statuts non actifs)
                      <ChevronDownIcon
                        className={`h-4 w-4 transition-transform duration-150 ease-out ${
                          prioritairesOuverts ? 'rotate-180' : ''
                        }`}
                        aria-hidden
                      />
                    </button>
                    {prioritairesOuverts && (
                      <div className="border-t border-albarka-border px-4 py-4">
                        <BlocAsync etat={prioritaires} squelette={<Squelette lignes={5} />}>
                          {(agents) => (
                            <DataTable
                              colonnes={[
                                { cle: 'posName',      entete: 'Agent'   },
                                { cle: 'posMsisdn',    entete: 'MSISDN'  },
                                { cle: 'dsmName',      entete: 'DSM'     },
                                { cle: 'segmentGroup', entete: 'Segment' },
                                { cle: 'town',         entete: 'Ville'   },
                                {
                                  cle: 'statut',
                                  entete: 'Statut',
                                  rendu: (a) => <StatusBadge statut={a.statut} />,
                                },
                              ]}
                              lignes={agents}
                              cleLigne={(a) => a.posMsisdn}
                              recherche
                              parPage={10}
                              compact
                            />
                          )}
                        </BlocAsync>
                      </div>
                    )}
                  </div>
                </div>
              ),
            },
            {
              id: 'hvc',
              libelle: 'HVC',
              contenu: (
                <div className="pt-2">
                  <TitreBloc>Agents HVC — Haut Volume Commercial</TitreBloc>
                  <ListeAgentsSegment dateRef={dateRef} dsmName={dsmName} segmentGroup="1-HVC" />
                </div>
              ),
            },
            {
              id: 'mvc',
              libelle: 'MVC',
              contenu: (
                <div className="pt-2">
                  <TitreBloc>Agents MVC — Moyen Volume Commercial</TitreBloc>
                  <ListeAgentsSegment dateRef={dateRef} dsmName={dsmName} segmentGroup="2-MVC" />
                </div>
              ),
            },
            {
              id: 'lvc',
              libelle: 'LVC',
              contenu: (
                <div className="pt-2">
                  <TitreBloc>Agents LVC — Bas Volume Commercial</TitreBloc>
                  <ListeAgentsSegment dateRef={dateRef} dsmName={dsmName} segmentGroup="3-LVC" />
                </div>
              ),
            },
          ]}
        />
      </div>
    </Section>
  );
}
