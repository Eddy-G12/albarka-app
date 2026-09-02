import React, { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Section, TitreBloc } from '../components/ui/Section';
import { SelecteurDateQr, SelecteurMois } from '../components/Filtres';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { BlocAsync, Squelette, SqueletteCartes } from '../components/ui/States';
import { DataTable } from '../components/DataTable';
import { StatusBadge } from '../components/StatusBadge';
import { CourbeEvolution } from '../components/charts/Charts';
import { useAuth } from '../contexts/AuthContext';
import { useFiltres } from '../contexts/FiltresContext';
import { useAsync } from '../hooks/useAsync';
import { getComparaisonQr, getRepartitionQr } from '../services/qr';
import { cashParCommercialSync } from '../services/cash';
import { classementAnonymise, LIBELLE_STATUT, ORDRE_STATUTS } from '../utils/business';
import { DATES_QR, MOIS_DISPONIBLES } from '../data/seed';
import { formatFcfa, formatNombre, formatPourcent, labelDate, labelMois } from '../utils/format';
import { TRANSACTIONS_MOMO } from '../data/operations';

export function MonDashboard() {
  const { commercial } = useAuth();
  const { dateQr, setDateQr, moisCash, setMoisCash } = useFiltres();
  const [dateComparaison, setDateComparaison] = useState(DATES_QR[DATES_QR.length - 2]);

  const dsmName = commercial?.dsmName;

  const qr = useAsync(() => getRepartitionQr(dateQr, dsmName), [dateQr, dsmName]);
  const comparaison = useAsync(
    () => getComparaisonQr(dateComparaison, dateQr),
    [dateComparaison, dateQr]
  );
  const cash = useAsync(async () => {
    const classement = cashParCommercialSync(moisCash);
    const mien = classement.find((l) => l.dsmName === dsmName);
    return {
      mien,
      anonymise: classementAnonymise(classement, dsmName ?? ''),
      historique: TRANSACTIONS_MOMO.filter((t) => t.commercialId === commercial?.id)
    };
  }, [moisCash, dsmName, commercial?.id]);

  if (!commercial) return null;

  return (
    <div>
      <PageHeader
        titre="Mon Dashboard"
        description={`Périmètre ${commercial.dsmName} — ${commercial.zone}. Les autres commerciaux restent anonymisés.`}
        filtres={
        <>
            <SelecteurDateQr valeur={dateQr} onChange={setDateQr} />
            <SelecteurDateQr
            label="Date de comparaison"
            valeur={dateComparaison}
            onChange={setDateComparaison}
            id="date-comparaison"
            dates={DATES_QR.filter((d) => d !== dateQr)} />
          
            <SelecteurMois label="Mois cash" valeur={moisCash} onChange={setMoisCash} />
          </>
        } />
      

      <div className="space-y-6">
        <Section
          titre="Mon périmètre QR Code"
          description={`Agents rattachés à ${commercial.dsmName} au ${labelDate(dateQr)}.`}>
          
          <BlocAsync etat={qr} squelette={<SqueletteCartes nb={5} />}>
            {({ agents, repartition }) =>
            <div className="space-y-5">
                <GrilleMetriques colonnes={5}>
                  <MetricCard
                  libelle="Mes agents"
                  valeur={formatNombre(repartition.total)}
                  principale />
                
                  <MetricCard libelle="Actifs" valeur={formatNombre(repartition.parStatut.actif)} />
                  <MetricCard libelle="À risque" valeur={formatNombre(repartition.parStatut.risque)} />
                  <MetricCard
                  libelle="Sans QR"
                  valeur={formatNombre(repartition.parStatut.sans_qr)} />
                
                  <MetricCard
                  libelle="Taux d'utilisation"
                  valeur={formatPourcent(repartition.tauxUtilisation)} />
                
                </GrilleMetriques>

                <DataTable
                colonnes={[
                { cle: 'posName', entete: 'Agent' },
                { cle: 'posMsisdn', entete: 'MSISDN' },
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
              
              </div>
            }
          </BlocAsync>
        </Section>

        <Section
          titre="Évolution de mon périmètre"
          description={`Statuts entre le ${labelDate(dateComparaison)} et le ${labelDate(dateQr)}.`}>
          
          <BlocAsync etat={comparaison} squelette={<Squelette lignes={4} />}>
            {(donnees) => {
              const lignes = ORDRE_STATUTS.map((statut) => ({
                statut,
                libelle: LIBELLE_STATUT[statut],
                avant: donnees.repartitionA.parStatut[statut],
                apres: donnees.repartitionB.parStatut[statut]
              }));
              return (
                <DataTable
                  colonnes={[
                  { cle: 'libelle', entete: 'Statut' },
                  { cle: 'avant', entete: labelDate(dateComparaison), numerique: true },
                  { cle: 'apres', entete: labelDate(dateQr), numerique: true },
                  {
                    cle: 'evolution',
                    entete: 'Évolution',
                    numerique: true,
                    valeur: (l) => l.apres - l.avant,
                    rendu: (l) => {
                      const delta = l.apres - l.avant;
                      return (
                        <span
                          className={
                          delta > 0 ?
                          'text-statut-actif' :
                          delta < 0 ?
                          'text-[#C0392B]' :
                          'text-albarka-muted'
                          }>
                          
                            {delta > 0 ? '+' : ''}
                            {delta}
                          </span>);

                    }
                  }]
                  }
                  lignes={lignes}
                  cleLigne={(l) => l.statut}
                  parPage={4}
                  compact />);


            }}
          </BlocAsync>
        </Section>

        <Section
          titre="Mes cash in / cash out"
          description={`Vos commissions sur ${labelMois(moisCash)} et votre position dans le classement réseau.`}>
          
          <BlocAsync etat={cash} squelette={<SqueletteCartes nb={3} />}>
            {({ mien, anonymise, historique }) =>
            <div className="space-y-6">
                <GrilleMetriques colonnes={3}>
                  <MetricCard
                  libelle="Mon Cash In"
                  valeur={formatFcfa(mien?.cashIn ?? 0)}
                  unite="FCFA"
                  principale />
                
                  <MetricCard
                  libelle="Mon Cash Out"
                  valeur={formatFcfa(mien?.cashOut ?? 0)}
                  unite="FCFA" />
                
                  <MetricCard
                  libelle="Mon rang"
                  valeur={`#${anonymise.position}`}
                  detail={`sur ${anonymise.total} commerciaux`} />
                
                </GrilleMetriques>

                <div>
                  <TitreBloc>Classement anonymisé (voisins ±2)</TitreBloc>
                  <DataTable
                  colonnes={[
                  { cle: 'position', entete: 'Rang', numerique: true },
                  { cle: 'libelle', entete: 'Commercial' },
                  {
                    cle: 'cashIn',
                    entete: 'Cash In',
                    numerique: true,
                    rendu: (l) => formatFcfa(l.cashIn)
                  },
                  {
                    cle: 'cashOut',
                    entete: 'Cash Out',
                    numerique: true,
                    rendu: (l) => formatFcfa(l.cashOut)
                  }]
                  }
                  lignes={anonymise.lignes}
                  cleLigne={(l) => `rang-${l.position}`}
                  ligneSurlignee={(l) => l.estMoi}
                  parPage={5}
                  compact />
                
                </div>

                <div>
                  <TitreBloc>Mon évolution mensuelle</TitreBloc>
                  <CourbeEvolution
                  donnees={MOIS_DISPONIBLES.map((mois) => {
                    const ligne = historique.find((h) => h.mois === mois);
                    return {
                      mois: labelMois(mois),
                      cashIn: ligne?.cashIn ?? 0,
                      cashOut: ligne?.cashOut ?? 0
                    };
                  })}
                  cleLabel="mois"
                  series={[
                  { cle: 'cashIn', nom: 'Cash In', couleur: '#F5A623' },
                  { cle: 'cashOut', nom: 'Cash Out', couleur: '#1A1A1A' }]
                  } />
                
                </div>
              </div>
            }
          </BlocAsync>
        </Section>
      </div>
    </div>);

}