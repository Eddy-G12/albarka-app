import React, { useState } from 'react';
import { DownloadIcon, EraserIcon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Section, TitreBloc } from '../components/ui/Section';
import { Tabs } from '../components/ui/Tabs';
import { Button } from '../components/ui/Button';
import { Champ, Select } from '../components/ui/Field';
import { FileDropzone } from '../components/FileDropzone';
import { DataTable } from '../components/DataTable';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { BarresHorizontales } from '../components/charts/Charts';
import { BlocAsync, EtatVide, Squelette } from '../components/ui/States';
import { useAuth } from '../contexts/AuthContext';
import { useAsync } from '../hooks/useAsync';
import { getReactivite } from '../services/terrain';
import { store } from '../services/store';
import type { ReactiviteIndicateur } from '../types';
import { formatMinutes, formatNombre } from '../utils/format';
import { somme } from '../utils/business';
import { exporterExcel } from '../utils/export';

function GraphiqueIndicateur({
  lignes,
  cle,
  monetaire = false




}: {lignes: ReactiviteIndicateur[];cle: keyof ReactiviteIndicateur;monetaire?: boolean;}) {
  const donnees = lignes.
  filter((l) => l[cle] !== null).
  map((l) => ({ dsmName: l.dsmName, valeur: Number(l[cle]) })).
  sort((a, b) => b.valeur - a.valeur);

  if (!donnees.length) {
    return (
      <EtatVide
        titre="Données insuffisantes"
        message="Cet indicateur nécessite l'horodatage complet et la colonne Balance des CSV bruts." />);


  }

  return (
    <BarresHorizontales
      donnees={donnees}
      cleLabel="dsmName"
      cleValeur="valeur"
      monetaire={monetaire}
      hauteur={260} />);


}

export function Reactivite() {
  const { peutDeposer } = useAuth();
  const [efface, setEfface] = useState(false);
  const [fiche, setFiche] = useState<string>('');
  const reactivite = useAsync(() => getReactivite(), [efface]);

  return (
    <div>
      <PageHeader
        titre="Réactivité Commerciale"
        description="Rythme de travail relevé sur les CSV bruts MTN : cadence, clients touchés, temps morts et temps de recharge."
        actions={
        <Button
          icone={<EraserIcon className="h-4 w-4" />}
          onClick={() => setEfface((v) => !v)}>
          
            Effacer les résultats
          </Button>
        } />
      

      <div className="space-y-6">
        {peutDeposer &&
        <Section
          titre="Dépôt des CSV bruts"
          description="L'alias configuré en base permet d'associer chaque fichier à son commercial ; l'association reste modifiable.">
          
            <FileDropzone
            accept=".csv"
            legende="Fichiers CSV bruts MTN avec horodatage complet et colonne Balance (ex. STEPHANE(7).csv)."
            commerciaux={store.commerciaux.map((c) => ({ dsmName: c.dsmName, alias: c.alias }))} />
          
          </Section>
        }

        <BlocAsync etat={reactivite} squelette={<Squelette lignes={8} />}>
          {(lignes) => {
            const selectionne = lignes.find((l) => l.dsmName === fiche) ?? lignes[0];
            return (
              <>
                <Section
                  titre="Synthèse réseau"
                  description="Moyennes calculées sur les commerciaux disposant de données exploitables.">
                  
                  <GrilleMetriques colonnes={4}>
                    <MetricCard
                      libelle="Transactions analysées"
                      valeur={formatNombre(somme(lignes.map((l) => l.nbTransactions)))}
                      principale />
                    
                    <MetricCard
                      libelle="Tx / jour moyen"
                      valeur={formatNombre(somme(lignes.map((l) => l.txParJour)) / lignes.length)} />
                    
                    <MetricCard
                      libelle="Clients / jour moyen"
                      valeur={formatNombre(somme(lignes.map((l) => l.clientsParJour)) / lignes.length)} />
                    
                    <MetricCard
                      libelle="Temps mort médian réseau"
                      valeur={formatMinutes(
                        somme(lignes.map((l) => l.tempsMortMedian ?? 0)) / (
                        lignes.filter((l) => l.tempsMortMedian !== null).length || 1)
                      )} />
                    
                  </GrilleMetriques>
                </Section>

                <Section
                  titre="Indicateurs par commercial"
                  description="« N/A » signale un indicateur non calculable faute de données suffisantes dans le CSV.">
                  
                  <DataTable
                    colonnes={[
                    { cle: 'dsmName', entete: 'Commercial' },
                    { cle: 'nbTransactions', entete: 'Nb tx', numerique: true },
                    { cle: 'joursActifs', entete: 'Jours actifs', numerique: true },
                    { cle: 'txParJour', entete: 'Tx / jour', numerique: true },
                    { cle: 'clientsParJour', entete: 'Clients / jour', numerique: true },
                    {
                      cle: 'tempsMortMedian',
                      entete: 'Temps mort médian',
                      numerique: true,
                      rendu: (l) => formatMinutes(l.tempsMortMedian)
                    },
                    {
                      cle: 'tempsMortMax',
                      entete: 'Temps mort max',
                      numerique: true,
                      rendu: (l) => formatMinutes(l.tempsMortMax)
                    },
                    {
                      cle: 'tempsRechargeMedian',
                      entete: 'Recharge médiane',
                      numerique: true,
                      rendu: (l) => formatMinutes(l.tempsRechargeMedian)
                    },
                    {
                      cle: 'tempsRechargeMin',
                      entete: 'Recharge la + rapide',
                      numerique: true,
                      rendu: (l) => formatMinutes(l.tempsRechargeMin)
                    }]
                    }
                    lignes={lignes}
                    cleLigne={(l) => `reac-${l.commercialId}`}
                    parPage={12}
                    onExport={() =>
                    exporterExcel('reactivite-commerciale', [
                    {
                      nom: 'Synthèse réseau',
                      lignes: [
                      {
                        'Transactions analysées': somme(lignes.map((l) => l.nbTransactions)),
                        'Tx / jour moyen': Number(
                          (somme(lignes.map((l) => l.txParJour)) / lignes.length).toFixed(1)
                        ),
                        Commerciaux: lignes.length
                      }]

                    },
                    {
                      nom: 'Par commercial',
                      lignes: lignes.map((l) => ({
                        Commercial: l.dsmName,
                        'Nb transactions': l.nbTransactions,
                        'Jours actifs': l.joursActifs,
                        'Tx / jour': l.txParJour,
                        'Clients / jour': l.clientsParJour,
                        'Temps mort médian (min)': l.tempsMortMedian ?? 'N/A',
                        'Temps mort max (min)': l.tempsMortMax ?? 'N/A',
                        'Recharge médiane (min)': l.tempsRechargeMedian ?? 'N/A',
                        'Recharge min (min)': l.tempsRechargeMin ?? 'N/A'
                      }))
                    }]
                    )
                    } />
                  
                </Section>

                <Section titre="Lecture graphique">
                  <Tabs
                    onglets={[
                    {
                      id: 'tx',
                      libelle: 'Transactions / jour',
                      contenu: <GraphiqueIndicateur lignes={lignes} cle="txParJour" />
                    },
                    {
                      id: 'clients',
                      libelle: 'Clients / jour',
                      contenu: <GraphiqueIndicateur lignes={lignes} cle="clientsParJour" />
                    },
                    {
                      id: 'mort',
                      libelle: 'Temps mort',
                      contenu: <GraphiqueIndicateur lignes={lignes} cle="tempsMortMedian" />
                    },
                    {
                      id: 'recharge',
                      libelle: 'Temps de recharge',
                      contenu: <GraphiqueIndicateur lignes={lignes} cle="tempsRechargeMedian" />
                    }]
                    } />
                  
                </Section>

                <Section
                  titre="Fiche individuelle"
                  actions={
                  <Champ label="Commercial" htmlFor="fiche" className="w-52">
                      <Select
                      id="fiche"
                      value={selectionne?.dsmName ?? ''}
                      onChange={(e) => setFiche(e.target.value)}>
                      
                        {lignes.map((l) =>
                      <option key={l.commercialId} value={l.dsmName}>
                            {l.dsmName}
                          </option>
                      )}
                      </Select>
                    </Champ>
                  }>
                  
                  {selectionne ?
                  <div className="space-y-4">
                      <TitreBloc>{selectionne.dsmName}</TitreBloc>
                      <GrilleMetriques colonnes={4}>
                        <MetricCard
                        libelle="Transactions"
                        valeur={formatNombre(selectionne.nbTransactions)}
                        detail={`${selectionne.joursActifs} jours actifs`}
                        principale />
                      
                        <MetricCard
                        libelle="Cadence"
                        valeur={formatNombre(selectionne.txParJour)}
                        unite="tx/j" />
                      
                        <MetricCard
                        libelle="Temps mort médian"
                        valeur={formatMinutes(selectionne.tempsMortMedian)}
                        detail={`max ${formatMinutes(selectionne.tempsMortMax)}`} />
                      
                        <MetricCard
                        libelle="Temps de recharge"
                        valeur={formatMinutes(selectionne.tempsRechargeMedian)}
                        detail={`plus rapide ${formatMinutes(selectionne.tempsRechargeMin)}`} />
                      
                      </GrilleMetriques>
                      <Button icone={<DownloadIcon className="h-4 w-4" />} taille="sm">
                        Exporter la fiche
                      </Button>
                    </div> :

                  <EtatVide
                    titre="Aucun commercial analysé"
                    message="Déposez des CSV bruts MTN pour produire les indicateurs de réactivité." />

                  }
                </Section>
              </>);

          }}
        </BlocAsync>
      </div>
    </div>);

}