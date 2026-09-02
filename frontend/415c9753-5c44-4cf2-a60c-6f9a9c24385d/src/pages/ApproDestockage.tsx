import React, { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Tabs } from '../components/ui/Tabs';
import { Section, TitreBloc } from '../components/ui/Section';
import { SelecteurCommercial, SelecteurMois } from '../components/Filtres';
import { Champ, Select } from '../components/ui/Field';
import { SectionAppro } from '../components/dashboard/SectionAppro';
import { DataTable } from '../components/DataTable';
import { CourbeEvolution } from '../components/charts/Charts';
import { BlocAsync, Squelette } from '../components/ui/States';
import { useAuth } from '../contexts/AuthContext';
import { useFiltres } from '../contexts/FiltresContext';
import { useAsync } from '../hooks/useAsync';
import { getDetailAppro, getEvolutionAppro } from '../services/cash';
import { store } from '../services/store';
import { MOIS_COURANT } from '../data/seed';
import type { TypeOp } from '../types';
import { formatFcfa, labelDate, labelMois } from '../utils/format';
import { exporterExcel } from '../utils/export';

function OngletEvolution({ commercialId }: {commercialId?: number;}) {
  const evolution = useAsync(() => getEvolutionAppro(commercialId), [commercialId]);

  return (
    <Section
      titre="Évolution mensuelle"
      description="Tendance des mouvements de flotte sur les mois disponibles.">
      
      <BlocAsync etat={evolution} squelette={<Squelette lignes={5} />}>
        {(series) =>
        <div className="space-y-6">
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
          
            <div>
              <TitreBloc>Pivot mois × montants</TitreBloc>
              <DataTable
              colonnes={[
              { cle: 'mois', entete: 'Mois', rendu: (l) => labelMois(l.mois) },
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
              lignes={series}
              cleLigne={(l) => l.mois}
              parPage={12}
              compact />
            
            </div>
          </div>
        }
      </BlocAsync>
    </Section>);

}

function OngletDetail({ commercialImpose }: {commercialImpose?: number;}) {
  const [commercialId, setCommercialId] = useState<number | 'tous'>(commercialImpose ?? 'tous');
  const [mois, setMois] = useState(MOIS_COURANT);
  const [typeOp, setTypeOp] = useState<TypeOp | 'tous'>('tous');

  const detail = useAsync(
    () =>
    getDetailAppro({
      commercialId: commercialImpose ?? (commercialId === 'tous' ? undefined : commercialId),
      mois,
      typeOp: typeOp === 'tous' ? undefined : typeOp
    }),
    [commercialImpose, commercialId, mois, typeOp]
  );

  return (
    <Section
      titre="Détail journalier"
      description="Chaque ligne provient d'un TCD du classeur transactions généré au dépôt du CSV."
      actions={
      <>
          {!commercialImpose &&
        <SelecteurCommercial
          valeur={commercialId}
          onChange={setCommercialId}
          commerciaux={store.commerciaux.filter((c) => c.alias)} />

        }
          <SelecteurMois valeur={mois} onChange={setMois} id="mois-detail" />
          <Champ label="Type" htmlFor="type-op" className="w-40">
            <Select
            id="type-op"
            value={typeOp}
            onChange={(e) => setTypeOp(e.target.value as TypeOp | 'tous')}>
            
              <option value="tous">Tous les types</option>
              <option value="appro">Appro</option>
              <option value="destockage">Destockage</option>
            </Select>
          </Champ>
        </>
      }>
      
      <BlocAsync etat={detail} squelette={<Squelette lignes={8} hauteur="h-6" />}>
        {(lignes) =>
        <DataTable
          colonnes={[
          { cle: 'dsmName', entete: 'Commercial' },
          { cle: 'dateOp', entete: 'Date', rendu: (l) => labelDate(l.dateOp) },
          {
            cle: 'typeOp',
            entete: 'Type',
            rendu: (l) => l.typeOp === 'appro' ? 'Appro' : 'Destockage'
          },
          { cle: 'nbOps', entete: 'Nb ops', numerique: true },
          {
            cle: 'montant',
            entete: 'Montant',
            numerique: true,
            rendu: (l) => formatFcfa(l.montant)
          },
          { cle: 'sourceFichier', entete: 'Fichier source' }]
          }
          lignes={lignes}
          cleLigne={(l) => `detail-${l.id}`}
          recherche
          parPage={15}
          compact
          onExport={() =>
          exporterExcel(`detail-appro-${mois}`, [
          {
            nom: 'Détail journalier',
            lignes: lignes.map((l) => ({
              Commercial: l.dsmName,
              Date: l.dateOp,
              Type: l.typeOp,
              'Nb ops': l.nbOps,
              Montant: l.montant,
              Fichier: l.sourceFichier ?? null
            }))
          }]
          )
          } />

        }
      </BlocAsync>
    </Section>);

}

export function ApproDestockage() {
  const { commercial, estCommercial } = useAuth();
  const { moisAppro, setMoisAppro } = useFiltres();
  const commercialId = estCommercial ? commercial?.id : undefined;

  return (
    <div>
      <PageHeader
        titre="Appro / Destockage"
        description={
        estCommercial ?
        'Vos mouvements de flotte, calculés depuis les TCD de vos classeurs transactions.' :
        'Mouvements de flotte du réseau, calculés depuis les TCD des classeurs transactions.'
        }
        filtres={<SelecteurMois label="Mois" valeur={moisAppro} onChange={setMoisAppro} />} />
      
      <Tabs
        onglets={[
        {
          id: 'dashboard',
          libelle: 'Dashboard mensuel',
          contenu: <SectionAppro mois={moisAppro} commercialId={commercialId} />
        },
        {
          id: 'evolution',
          libelle: 'Évolution mensuelle',
          contenu: <OngletEvolution commercialId={commercialId} />
        },
        {
          id: 'detail',
          libelle: 'Détail journalier',
          contenu: <OngletDetail commercialImpose={commercialId} />
        }]
        } />
      
    </div>);

}