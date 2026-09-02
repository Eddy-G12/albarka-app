import React, { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Tabs } from '../components/ui/Tabs';
import { Section, TitreBloc } from '../components/ui/Section';
import { FileDropzone } from '../components/FileDropzone';
import { DataTable } from '../components/DataTable';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { SelecteurCommercial } from '../components/Filtres';
import { Champ, Input } from '../components/ui/Field';
import { BlocAsync, Squelette } from '../components/ui/States';
import { useAuth } from '../contexts/AuthContext';
import { useAsync } from '../hooks/useAsync';
import { getClientsServis, getSynthesePointsTouches } from '../services/terrain';
import { store } from '../services/store';
import { formatNombre, labelDate } from '../utils/format';
import { exporterExcel } from '../utils/export';

function OngletImport() {
  const sansAlias = store.commerciaux.filter((c) => !c.alias).map((c) => c.dsmName);

  return (
    <div className="space-y-4">
      <Section
        titre="Dépôt des CSV bruts MTN"
        description="Un fichier par commercial. Nettoyage automatique (Type = Transfer, hors ALBARKA GN SARL) puis génération d'un classeur 3 onglets : Données, TCD - To Name, TCD - From Name.">
        
        <FileDropzone
          accept=".csv"
          legende="Le commercial est déduit du nom du fichier (ex. ANTOINE.csv → ANTOINE) et reste modifiable."
          commerciaux={store.commerciaux.map((c) => ({ dsmName: c.dsmName, alias: c.alias }))} />
        
      </Section>

      {sansAlias.length > 0 &&
      <p className="rounded-md border border-albarka-border bg-albarka-bg px-4 py-3 text-xs text-albarka-muted">
          {sansAlias.join(', ')} n'ont pas d'alias CSV configuré : leurs clients servis et leurs
          appros / destockages ne pourront pas être extraits. Configurez l'alias dans
          Administration → Aliases CSV.
        </p>
      }
    </div>);

}

function OngletPoints({ commercialImpose }: {commercialImpose?: number;}) {
  const points = useAsync(() => getSynthesePointsTouches(commercialImpose), [commercialImpose]);

  return (
    <Section
      titre="Points touchés"
      description="Nombre de lignes traitées par jour, par commercial, depuis les classeurs générés.">
      
      <BlocAsync etat={points} squelette={<Squelette lignes={8} />}>
        {(donnees) =>
        <div className="space-y-6">
            <div>
              <TitreBloc>Synthèse par commercial</TitreBloc>
              <DataTable
              colonnes={[
              { cle: 'dsmName', entete: 'Commercial' },
              { cle: 'totalPoints', entete: 'Total points', numerique: true },
              { cle: 'joursActifs', entete: 'Jours actifs', numerique: true },
              { cle: 'moyenneJour', entete: 'Moyenne / jour', numerique: true }]
              }
              lignes={donnees.parCommercial}
              cleLigne={(l) => `pt-${l.commercialId}`}
              parPage={10}
              compact
              onExport={() =>
              exporterExcel('points-touches', [
              {
                nom: 'Synthèse',
                lignes: donnees.parCommercial.map((l) => ({
                  Commercial: l.dsmName,
                  'Total points': l.totalPoints,
                  'Jours actifs': l.joursActifs,
                  'Moyenne / jour': l.moyenneJour
                }))
              },
              {
                nom: 'Détail journalier',
                lignes: donnees.detail.map((l) => ({
                  Commercial: l.dsmName,
                  Date: l.dateOp,
                  'Points touchés': l.nbPoints
                }))
              }]
              )
              } />
            
            </div>
            <div>
              <TitreBloc>Détail journalier</TitreBloc>
              <DataTable
              colonnes={[
              { cle: 'dsmName', entete: 'Commercial' },
              { cle: 'dateOp', entete: 'Date', rendu: (l) => labelDate(l.dateOp) },
              { cle: 'nbPoints', entete: 'Points touchés', numerique: true }]
              }
              lignes={donnees.detail}
              cleLigne={(l, i) => `detail-pt-${l.commercialId}-${l.dateOp}-${i}`}
              recherche
              parPage={15}
              compact />
            
            </div>
          </div>
        }
      </BlocAsync>
    </Section>);

}

function OngletClients({ commercialImpose }: {commercialImpose?: number;}) {
  const [commercialId, setCommercialId] = useState<number | 'tous'>(commercialImpose ?? 'tous');
  const [du, setDu] = useState('2026-08-01');
  const [au, setAu] = useState('2026-08-31');

  const clients = useAsync(
    () =>
    getClientsServis({
      commercialId: commercialImpose ?? (commercialId === 'tous' ? undefined : commercialId),
      du,
      au
    }),
    [commercialImpose, commercialId, du, au]
  );

  return (
    <Section
      titre="Clients servis"
      description="Contreparties relevées dans les CSV bruts, hors alias du commercial et hors comptes ALBARKA."
      actions={
      <>
          {!commercialImpose &&
        <SelecteurCommercial
          valeur={commercialId}
          onChange={setCommercialId}
          commerciaux={store.commerciaux.filter((c) => c.alias)} />

        }
          <Champ label="Du" htmlFor="du" className="w-40">
            <Input id="du" type="date" value={du} onChange={(e) => setDu(e.target.value)} />
          </Champ>
          <Champ label="Au" htmlFor="au" className="w-40">
            <Input id="au" type="date" value={au} onChange={(e) => setAu(e.target.value)} />
          </Champ>
        </>
      }>
      
      <BlocAsync etat={clients} squelette={<Squelette lignes={8} />}>
        {(donnees) =>
        <div className="space-y-5">
            <GrilleMetriques colonnes={2}>
              <MetricCard
              libelle="Clients distincts"
              valeur={formatNombre(donnees.clientsDistincts)}
              principale />
            
              <MetricCard
              libelle="Total transactions"
              valeur={formatNombre(donnees.totalTransactions)} />
            
            </GrilleMetriques>
            <DataTable
            colonnes={[
            { cle: 'msisdn', entete: 'MSISDN' },
            { cle: 'nom', entete: 'Nom' },
            { cle: 'nbTransactions', entete: 'Nb transactions', numerique: true },
            { cle: 'premiere', entete: 'Première date', rendu: (l) => labelDate(l.premiere) },
            { cle: 'derniere', entete: 'Dernière date', rendu: (l) => labelDate(l.derniere) }]
            }
            lignes={donnees.lignes}
            cleLigne={(l) => `client-${l.msisdn}`}
            recherche
            parPage={15}
            compact
            onExport={() =>
            exporterExcel('clients-servis', [
            {
              nom: 'Clients servis',
              lignes: donnees.lignes.map((l) => ({
                MSISDN: l.msisdn,
                Nom: l.nom,
                'Nb transactions': l.nbTransactions,
                'Première date': l.premiere,
                'Dernière date': l.derniere
              }))
            }]
            )
            } />
          
          </div>
        }
      </BlocAsync>
    </Section>);

}

export function Transactions() {
  const { peutDeposer, estCommercial, commercial } = useAuth();
  const commercialId = estCommercial ? commercial?.id : undefined;

  return (
    <div>
      <PageHeader
        titre="Transactions"
        description="Traitement des CSV bruts MTN : nettoyage, classeurs Excel, points touchés et clients servis." />
      
      <Tabs
        onglets={[
        ...(peutDeposer ? [{ id: 'import', libelle: 'Import', contenu: <OngletImport /> }] : []),
        {
          id: 'points',
          libelle: 'Points touchés',
          contenu: <OngletPoints commercialImpose={commercialId} />
        },
        {
          id: 'clients',
          libelle: 'Clients servis',
          contenu: <OngletClients commercialImpose={commercialId} />
        }]
        } />
      
    </div>);

}