import React, { useState } from 'react';
import { toast } from 'sonner';
import { UploadCloudIcon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Section, TitreBloc } from '../components/ui/Section';
import { Tabs } from '../components/ui/Tabs';
import { Champ, Select } from '../components/ui/Field';
import { SelecteurMois } from '../components/Filtres';
import { Button } from '../components/ui/Button';
import { DataTable } from '../components/DataTable';
import { BarresHorizontales } from '../components/charts/Charts';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { BlocAsync, EtatVide, Squelette } from '../components/ui/States';
import { useAuth } from '../contexts/AuthContext';
import { useAsync } from '../hooks/useAsync';
import {
  getAlertesSeuilPos,
  getClassementPos,
  getComparaisonMoMPos } from
'../services/cash';
import { MOIS_COURANT, MOIS_DISPONIBLES } from '../data/seed';
import { formatFcfa, formatNombre, labelMois } from '../utils/format';
import { exporterExcel } from '../utils/export';

function OngletImport() {
  const [fichier, setFichier] = useState<File | null>(null);
  const [mois, setMois]       = useState('');
  const [loading, setLoading] = useState(false);
  const [resultat, setResultat] = useState<{ mois: string; nb_pos: number; total_cash_in: number; total_cash_out: number } | null>(null);

  const lancer = async () => {
    if (!fichier) { toast.error('Sélectionnez un fichier SAE.'); return; }
    setLoading(true);
    try {
      const { importerSae } = await import('../services/import');
      const res = await importerSae(fichier, mois || undefined);
      setResultat(res);
      toast.success(`Import réussi — ${res.nb_pos} POS — mois ${res.mois}`);
    } catch (err) {
      toast.error(`Erreur : ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Section
      titre="Import du fichier SAE MTN"
      description="Feuille 1 ignorée, lecture de Sheet1 (731 POS). Le mois est détecté depuis le nom du fichier puis confirmé."
    >
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <Champ label="Mois (optionnel)" htmlFor="mois-sae" className="w-40">
          <input
            id="mois-sae"
            type="month"
            value={mois}
            onChange={(e) => setMois(e.target.value)}
            className="w-full rounded border border-albarka-border px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-albarka-black"
            placeholder="2026-08"
          />
        </Champ>
      </div>

      <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-albarka-black transition-colors bg-gray-50">
        <UploadCloudIcon className="h-6 w-6 text-gray-400 mb-1" />
        <span className="text-sm text-gray-500">
          {fichier ? fichier.name : 'Cliquez pour sélectionner le fichier SAE (.xlsx ou .csv)'}
        </span>
        <input
          type="file"
          accept=".xlsx,.csv"
          className="hidden"
          onChange={(e) => setFichier(e.target.files?.[0] ?? null)}
        />
      </label>

      <Button
        variante="primaire"
        onClick={lancer}
        disabled={!fichier || loading}
        className="mt-4"
      >
        {loading ? 'Import en cours…' : 'Importer'}
      </Button>

      {resultat && (
        <div className="mt-4 rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          <strong>Mois {resultat.mois}</strong> — {formatNombre(resultat.nb_pos)} POS —
          Cash In : {formatFcfa(resultat.total_cash_in)} FCFA —
          Cash Out : {formatFcfa(resultat.total_cash_out)} FCFA
        </div>
      )}
    </Section>
  );
}

function OngletClassements() {
  const [mois, setMois] = useState(MOIS_COURANT);
  const [flux, setFlux] = useState<'cashIn' | 'cashOut'>('cashIn');
  const [n, setN] = useState(15);
  const classement = useAsync(() => getClassementPos(mois, flux, n), [mois, flux, n]);

  return (
    <Section
      titre="Classements POS"
      description="Top et flop des points de vente sur la commission sélectionnée."
      actions={
      <>
          <SelecteurMois valeur={mois} onChange={setMois} id="mois-classement" />
          <Champ label="Flux" htmlFor="flux" className="w-36">
            <Select
            id="flux"
            className="h-8 text-xs"
            value={flux}
            onChange={(e) => setFlux(e.target.value as 'cashIn' | 'cashOut')}>
            
              <option value="cashIn">Cash In</option>
              <option value="cashOut">Cash Out</option>
            </Select>
          </Champ>
          <Champ label="Nombre de POS" htmlFor="nb-pos" className="w-32">
            <Select
            id="nb-pos"
            className="h-8 text-xs"
            value={n}
            onChange={(e) => setN(Number(e.target.value))}>
            
              {[5, 10, 15, 20, 30, 50].map((v) =>
            <option key={v} value={v}>
                  {v}
                </option>
            )}
            </Select>
          </Champ>
        </>
      }>
      
      <BlocAsync etat={classement} squelette={<Squelette lignes={8} hauteur="h-6" />}>
        {(donnees) =>
        <div className="space-y-6">
            <BarresHorizontales
            donnees={donnees.top.map((p) => ({
              agentName: `${p.agentName.slice(0, 22)}`,
              valeur: p[flux]
            }))}
            cleLabel="agentName"
            cleValeur="valeur"
            hauteur={Math.max(260, donnees.top.length * 22)} />
          
            <div className="grid gap-5 xl:grid-cols-2">
              <div>
                <TitreBloc>Top {n}</TitreBloc>
                <DataTable
                colonnes={[
                { cle: 'acceptorId', entete: 'Acceptor ID' },
                { cle: 'agentName', entete: 'Agent' },
                {
                  cle: flux,
                  entete: flux === 'cashIn' ? 'Cash In' : 'Cash Out',
                  numerique: true,
                  rendu: (p) => formatFcfa(p[flux])
                }]
                }
                lignes={donnees.top}
                cleLigne={(p) => `top-${p.acceptorId}`}
                parPage={n}
                compact />
              
              </div>
              <div>
                <TitreBloc>Flop {n}</TitreBloc>
                <DataTable
                colonnes={[
                { cle: 'acceptorId', entete: 'Acceptor ID' },
                { cle: 'agentName', entete: 'Agent' },
                {
                  cle: flux,
                  entete: flux === 'cashIn' ? 'Cash In' : 'Cash Out',
                  numerique: true,
                  rendu: (p) => formatFcfa(p[flux])
                }]
                }
                lignes={donnees.flop}
                cleLigne={(p) => `flop-${p.acceptorId}`}
                parPage={n}
                compact
                onExport={() =>
                exporterExcel(`classement-pos-${mois}`, [
                {
                  nom: `Top ${n}`,
                  lignes: donnees.top.map((p) => ({
                    AcceptorID: p.acceptorId,
                    Agent: p.agentName,
                    MSISDN: p.agentMsisdn,
                    'Cash In': p.cashIn,
                    'Cash Out': p.cashOut
                  }))
                },
                {
                  nom: `Flop ${n}`,
                  lignes: donnees.flop.map((p) => ({
                    AcceptorID: p.acceptorId,
                    Agent: p.agentName,
                    'Cash In': p.cashIn,
                    'Cash Out': p.cashOut
                  }))
                }]
                )
                } />
              
              </div>
            </div>
            <p className="text-xs text-albarka-muted">
              {formatNombre(donnees.total)} POS importés pour {labelMois(mois)}.
            </p>
          </div>
        }
      </BlocAsync>
    </Section>);

}

function OngletAlertes() {
  const [mois, setMois] = useState(MOIS_COURANT);
  const alertes = useAsync(() => getAlertesSeuilPos(mois), [mois]);

  return (
    <Section
      titre="Alertes seuil"
      description="POS dont la commission cash in ou cash out passe sous le seuil configuré."
      actions={<SelecteurMois valeur={mois} onChange={setMois} id="mois-alertes" />}>
      
      <BlocAsync etat={alertes} squelette={<Squelette lignes={6} />}>
        {(donnees) =>
        <div className="space-y-4">
            <GrilleMetriques colonnes={3}>
              <MetricCard
              libelle="POS en alerte"
              valeur={formatNombre(donnees.lignes.length)}
              principale />
            
              <MetricCard libelle="Seuil cash in" valeur={formatFcfa(donnees.seuilIn)} unite="FCFA" />
              <MetricCard
              libelle="Seuil cash out"
              valeur={formatFcfa(donnees.seuilOut)}
              unite="FCFA" />
            
            </GrilleMetriques>
            <DataTable
            colonnes={[
            { cle: 'acceptorId', entete: 'Acceptor ID' },
            { cle: 'agentName', entete: 'Agent' },
            { cle: 'cashIn', entete: 'Cash In', numerique: true, rendu: (p) => formatFcfa(p.cashIn) },
            {
              cle: 'ecartIn',
              entete: 'Écart seuil CI',
              numerique: true,
              rendu: (p) =>
              <span className={p.ecartIn < 0 ? 'text-[#C0392B]' : ''}>
                      {formatFcfa(p.ecartIn)}
                    </span>

            },
            {
              cle: 'cashOut',
              entete: 'Cash Out',
              numerique: true,
              rendu: (p) => formatFcfa(p.cashOut)
            },
            {
              cle: 'ecartOut',
              entete: 'Écart seuil CO',
              numerique: true,
              rendu: (p) =>
              <span className={p.ecartOut < 0 ? 'text-[#C0392B]' : ''}>
                      {formatFcfa(p.ecartOut)}
                    </span>

            }]
            }
            lignes={donnees.lignes}
            cleLigne={(p) => `alerte-${p.acceptorId}`}
            recherche
            parPage={12}
            onExport={() =>
            exporterExcel(`alertes-pos-${mois}`, [
            {
              nom: 'Alertes seuil',
              lignes: donnees.lignes.map((p) => ({
                AcceptorID: p.acceptorId,
                Agent: p.agentName,
                'Cash In': p.cashIn,
                'Écart CI': p.ecartIn,
                'Cash Out': p.cashOut,
                'Écart CO': p.ecartOut
              }))
            }]
            )
            } />
          
          </div>
        }
      </BlocAsync>
    </Section>);

}

function OngletMoM() {
  const [moisSelectionnes, setMoisSelectionnes] = useState<string[]>(MOIS_DISPONIBLES.slice(-2));
  const comparaison = useAsync(
    () => getComparaisonMoMPos(moisSelectionnes),
    [moisSelectionnes.join('|')]
  );

  const basculer = (mois: string) => {
    setMoisSelectionnes((courant) => {
      if (courant.includes(mois)) {
        return courant.length > 2 ? courant.filter((m) => m !== mois) : courant;
      }
      return courant.length >= 3 ? [...courant.slice(1), mois] : [...courant, mois];
    });
  };

  return (
    <div className="space-y-6">
      <Section
        titre="Comparaison multi-fichiers"
        description="Déposez 2 ou 3 fichiers SAE de mois différents, ou comparez directement les mois déjà importés.">

        <p className="text-sm text-albarka-muted">
          Importez d'abord les fichiers SAE via l'onglet "Import", puis revenez ici pour comparer les mois disponibles.
        </p>
        <div className="mt-4">
          <TitreBloc>Mois déjà importés (2 à 3)</TitreBloc>
          <div className="flex flex-wrap gap-2">
            {MOIS_DISPONIBLES.map((mois) => {
              const actif = moisSelectionnes.includes(mois);
              return (
                <button
                  key={mois}
                  type="button"
                  aria-pressed={actif}
                  onClick={() => basculer(mois)}
                  className={`rounded-md border px-3 py-1.5 text-xs transition-colors duration-150 ease-out ${
                  actif ?
                  'border-albarka-yellow bg-albarka-yellow-soft font-semibold text-albarka-black' :
                  'border-albarka-border bg-white text-albarka-muted hover:text-albarka-black'}`
                  }>
                  
                  {labelMois(mois)}
                </button>);

            })}
          </div>
        </div>
      </Section>

      <BlocAsync etat={comparaison} squelette={<Squelette lignes={8} />}>
        {(donnees) =>
        <div className="space-y-6">
            <Section titre="Top 10 cumulé (cash in sur tous les mois)">
              <DataTable
              colonnes={[
              { cle: 'acceptorId', entete: 'Acceptor ID' },
              { cle: 'agentName', entete: 'Agent' },
              {
                cle: 'cumul',
                entete: 'Cumul Cash In',
                numerique: true,
                rendu: (l) => formatFcfa(l.cumul)
              }]
              }
              lignes={donnees.topCumule}
              cleLigne={(l) => `cumul-${l.acceptorId}`}
              parPage={10}
              compact
              onExport={() =>
              exporterExcel('comparaison-mom-pos', [
              {
                nom: 'Top cumulé',
                lignes: donnees.topCumule.map((l) => ({
                  AcceptorID: l.acceptorId,
                  Agent: l.agentName,
                  'Cumul cash in': l.cumul
                }))
              },
              ...donnees.mois.map((m) => ({
                nom: `Top 20 ${m}`,
                lignes: donnees.topParMois[m].map((p) => ({
                  AcceptorID: p.acceptorId,
                  Agent: p.agentName,
                  'Cash In': p.cashIn
                }))
              }))]
              )
              } />
            
            </Section>

            <div className="grid gap-6 xl:grid-cols-2">
              <Section titre="POS constants dans le Top 20">
                {donnees.constantsTop.length ?
              <ul className="num grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-albarka-ink">
                    {donnees.constantsTop.map((id) =>
                <li key={id}>{id}</li>
                )}
                  </ul> :

              <EtatVide
                titre="Aucun POS constant"
                message="Aucun point de vente ne figure dans le Top 20 de tous les mois sélectionnés." />

              }
              </Section>
              <Section titre="POS constants dans le Flop 10">
                {donnees.constantsFlop.length ?
              <ul className="num grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-albarka-ink">
                    {donnees.constantsFlop.map((id) =>
                <li key={id}>{id}</li>
                )}
                  </ul> :

              <EtatVide
                titre="Aucun POS constant"
                message="Aucun point de vente ne figure dans le Flop 10 de tous les mois sélectionnés." />

              }
              </Section>
            </div>
          </div>
        }
      </BlocAsync>
    </div>);

}

export function CashFlow() {
  const { peutDeposer } = useAuth();

  const onglets = [
  ...(peutDeposer ? [{ id: 'import', libelle: 'Import SAE', contenu: <OngletImport /> }] : []),
  { id: 'classements', libelle: 'Classements', contenu: <OngletClassements /> },
  { id: 'alertes', libelle: 'Alertes seuil', contenu: <OngletAlertes /> },
  { id: 'mom', libelle: 'Comparaison MoM', contenu: <OngletMoM /> }];


  return (
    <div>
      <PageHeader
        titre="Cash Flow"
        description="Commissions cash in / cash out des points de vente, issues du fichier SAE MTN mensuel." />
      
      <Tabs onglets={onglets} />
    </div>);

}