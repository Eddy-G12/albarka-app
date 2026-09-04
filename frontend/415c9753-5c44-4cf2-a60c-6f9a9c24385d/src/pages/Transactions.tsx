import React, { useState } from 'react';
import { toast } from 'sonner';
import { UploadCloudIcon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Tabs } from '../components/ui/Tabs';
import { Section, TitreBloc } from '../components/ui/Section';
import { DataTable } from '../components/DataTable';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { SelecteurCommercial } from '../components/Filtres';
import { Champ, Input } from '../components/ui/Field';
import { Button } from '../components/ui/Button';
import { BlocAsync, Squelette } from '../components/ui/States';
import { useAuth } from '../contexts/AuthContext';
import { useAsync } from '../hooks/useAsync';
import { getClientsServis, getSynthesePointsTouches } from '../services/terrain';
import { importerTransactions, type ResultatImportTx } from '../services/import';
import { store } from '../services/store';
import { formatNombre, labelDate } from '../utils/format';
import { exporterExcel } from '../utils/export';

function OngletImport() {
  const [fichiers, setFichiers]     = useState<File[]>([]);
  const [loading, setLoading]       = useState(false);
  const [resultats, setResultats]   = useState<ResultatImportTx[]>([]);
  const sansAlias = store.commerciaux.filter((c) => !c.alias).map((c) => c.dsmName);

  const lancer = async () => {
    if (fichiers.length === 0) { toast.error('Sélectionnez au moins un fichier CSV.'); return; }
    setLoading(true);
    try {
      const res = await importerTransactions(fichiers);
      setResultats(res);
      const ok = res.filter((r) => r.message === 'OK').length;
      toast.success(`${ok} / ${res.length} fichier(s) traité(s) avec succès.`);
    } catch (err) {
      toast.error(`Erreur : ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Section
        titre="Dépôt des CSV bruts MTN"
        description="Un fichier par commercial. Nettoyage automatique (Type = Transfer, hors ALBARKA GN SARL), classeur Excel, clients servis et appro/déstockage calculés automatiquement."
      >
        <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-albarka-black transition-colors bg-gray-50">
          <UploadCloudIcon className="h-6 w-6 text-gray-400 mb-1" />
          <span className="text-sm text-gray-500">
            {fichiers.length > 0
              ? `${fichiers.length} fichier(s) sélectionné(s)`
              : 'Cliquez pour sélectionner un ou plusieurs CSV'}
          </span>
          <input
            type="file"
            accept=".csv"
            multiple
            className="hidden"
            onChange={(e) => setFichiers(Array.from(e.target.files ?? []))}
          />
        </label>

        <Button
          variante="primaire"
          onClick={lancer}
          disabled={fichiers.length === 0 || loading}
          className="mt-4"
        >
          {loading ? 'Traitement en cours…' : 'Traiter les fichiers'}
        </Button>
      </Section>

      {sansAlias.length > 0 && (
        <p className="rounded-md border border-albarka-border bg-albarka-bg px-4 py-3 text-xs text-albarka-muted">
          {sansAlias.join(', ')} n'ont pas d'alias CSV configuré : leurs clients servis et leurs
          appros / destockages ne pourront pas être extraits. Configurez l'alias dans
          Administration → Aliases CSV.
        </p>
      )}

      {resultats.length > 0 && (
        <Section titre="Résultats du traitement">
          <div className="space-y-2">
            {resultats.map((r, i) => (
              <div
                key={i}
                className={`rounded-md border px-4 py-3 text-sm ${
                  r.message === 'OK'
                    ? 'border-green-200 bg-green-50 text-green-800'
                    : 'border-amber-200 bg-amber-50 text-amber-800'
                }`}
              >
                <strong>{r.fichier}</strong>
                {r.message === 'OK' ? (
                  <>
                    {' '}— {formatNombre(r.nb_lignes)} lignes ·{' '}
                    {r.points_par_jour.toFixed(1)} pts/jour
                    {r.commercial && ` · Commercial : ${r.commercial}`}
                    {r.nb_clients_servis > 0 && ` · ${r.nb_clients_servis} clients servis`}
                    {r.appro_ok && ' · Appro extrait'}
                  </>
                ) : (
                  <> — {r.message}</>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
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