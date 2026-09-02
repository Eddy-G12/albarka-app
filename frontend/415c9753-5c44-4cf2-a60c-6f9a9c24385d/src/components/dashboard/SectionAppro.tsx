import React from 'react';
import { Section, TitreBloc } from '../ui/Section';
import { BlocAsync, EtatVide, Squelette } from '../ui/States';
import { GrilleMetriques, MetricCard } from '../MetricCard';
import { BarresGroupees, CourbeEvolution } from '../charts/Charts';
import { DataTable } from '../DataTable';
import { useAsync } from '../../hooks/useAsync';
import { getApproParCommercial, getEvolutionAppro } from '../../services/cash';
import { formatFcfa, formatNombre, labelMois } from '../../utils/format';
import { somme } from '../../utils/business';
import { exporterExcel } from '../../utils/export';

export function SectionAppro({
  mois,
  commercialId



}: {mois: string;commercialId?: number;}) {
  const appro = useAsync(() => getApproParCommercial(mois, commercialId), [mois, commercialId]);
  const evolution = useAsync(() => getEvolutionAppro(commercialId), [commercialId]);

  return (
    <Section
      id="appro"
      titre="Appros / Destockages"
      description={`Flux de flotte calculés depuis les TCD des classeurs transactions — ${labelMois(mois)}.`}>
      
      <BlocAsync etat={appro} squelette={<Squelette lignes={4} hauteur="h-14" />}>
        {(lignes) =>
        lignes.length === 0 ?
        <EtatVide
          titre="Aucun mouvement sur ce mois"
          message="Les appros et destockages sont extraits des classeurs transactions. Déposez un CSV brut MTN pour un commercial disposant d'un alias." /> :


        <div className="space-y-6">
              <GrilleMetriques colonnes={4}>
                <MetricCard
              libelle="Nb appros"
              valeur={formatNombre(somme(lignes.map((l) => l.nbAppros)))} />
            
                <MetricCard
              libelle="Montant appros"
              valeur={formatFcfa(somme(lignes.map((l) => l.montantAppros)), true)}
              unite="FCFA"
              principale />
            
                <MetricCard
              libelle="Nb destockages"
              valeur={formatNombre(somme(lignes.map((l) => l.nbDestockages)))} />
            
                <MetricCard
              libelle="Montant destockages"
              valeur={formatFcfa(somme(lignes.map((l) => l.montantDestockages)), true)}
              unite="FCFA" />
            
              </GrilleMetriques>

              <div className="grid gap-5 xl:grid-cols-2">
                <div>
                  <TitreBloc>Montants par commercial</TitreBloc>
                  <BarresGroupees
                donnees={lignes.map((l) => ({
                  dsmName: l.dsmName,
                  appro: l.montantAppros,
                  destockage: l.montantDestockages
                }))}
                cleLabel="dsmName"
                series={[
                { cle: 'appro', nom: 'Appros', couleur: '#F5A623' },
                { cle: 'destockage', nom: 'Destockages', couleur: '#1A1A1A' }]
                } />
              
                </div>
                <div>
                  <TitreBloc>Nombre d'opérations</TitreBloc>
                  <BarresGroupees
                donnees={lignes.map((l) => ({
                  dsmName: l.dsmName,
                  appro: l.nbAppros,
                  destockage: l.nbDestockages
                }))}
                cleLabel="dsmName"
                monetaire={false}
                series={[
                { cle: 'appro', nom: 'Appros', couleur: '#F5A623' },
                { cle: 'destockage', nom: 'Destockages', couleur: '#6B7280' }]
                } />
              
                </div>
              </div>

              <div>
                <TitreBloc>Récapitulatif</TitreBloc>
                <DataTable
              colonnes={[
              { cle: 'dsmName', entete: 'Commercial' },
              { cle: 'nbAppros', entete: 'Nb appros', numerique: true },
              {
                cle: 'montantAppros',
                entete: 'Montant appros',
                numerique: true,
                rendu: (l) => formatFcfa(l.montantAppros)
              },
              { cle: 'nbDestockages', entete: 'Nb destoc.', numerique: true },
              {
                cle: 'montantDestockages',
                entete: 'Montant destoc.',
                numerique: true,
                rendu: (l) => formatFcfa(l.montantDestockages)
              }]
              }
              lignes={lignes}
              cleLigne={(l) => `appro-${l.commercialId}`}
              parPage={10}
              onExport={() =>
              exporterExcel(`appro-${mois}`, [
              {
                nom: 'Appro destockage',
                lignes: lignes.map((l) => ({
                  Commercial: l.dsmName,
                  'Nb appros': l.nbAppros,
                  'Montant appros': l.montantAppros,
                  'Nb destockages': l.nbDestockages,
                  'Montant destockages': l.montantDestockages
                }))
              }]
              )
              } />
            
              </div>

              <div>
                <TitreBloc>Évolution mensuelle</TitreBloc>
                <BlocAsync etat={evolution} squelette={<Squelette lignes={4} />}>
                  {(series) =>
              <CourbeEvolution
                donnees={series.map((s) => ({
                  mois: labelMois(s.mois),
                  appros: s.montantAppros,
                  destockages: s.montantDestockages
                }))}
                cleLabel="mois"
                series={[
                { cle: 'appros', nom: 'Appros', couleur: '#F5A623' },
                { cle: 'destockages', nom: 'Destockages', couleur: '#1A1A1A' }]
                } />

              }
                </BlocAsync>
              </div>
            </div>

        }
      </BlocAsync>
    </Section>);

}