import React, { useState } from 'react';
import { toast } from 'sonner';
import { DownloadIcon, UploadCloudIcon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Section, TitreBloc } from '../components/ui/Section';
import { Tabs } from '../components/ui/Tabs';
import { Button } from '../components/ui/Button';
import { DataTable } from '../components/DataTable';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { BarresHorizontales } from '../components/charts/Charts';
import { EtatVide, Squelette } from '../components/ui/States';
import { useAuth } from '../contexts/AuthContext';
import { getReactivite, calculerReactivite } from '../services/terrain';
import type { ReactiviteIndicateur } from '../types';
import { formatMinutes, formatNombre } from '../utils/format';
import { somme } from '../utils/business';
import { exporterExcel } from '../utils/export';

// ── Graphique indicateur ───────────────────────────────────────────────────────

function GraphiqueIndicateur({
  lignes,
  cle,
  titre,
}: {
  lignes: ReactiviteIndicateur[];
  cle: keyof ReactiviteIndicateur;
  titre: string;
}) {
  const donnees = lignes
    .filter((l) => l[cle] !== null && l[cle] !== undefined)
    .map((l) => ({ dsmName: l.dsmName, valeur: Number(l[cle]) }))
    .sort((a, b) => b.valeur - a.valeur);

  if (!donnees.length) {
    return (
      <EtatVide
        titre="Données insuffisantes"
        message="Cet indicateur nécessite l'horodatage complet et la colonne Balance des CSV bruts MTN."
      />
    );
  }

  return (
    <BarresHorizontales
      donnees={donnees}
      cleLabel="dsmName"
      cleValeur="valeur"
      monetaire={false}
      hauteur={260}
      titre={titre}
    />
  );
}

// ── Page principale ────────────────────────────────────────────────────────────

export function Reactivite() {
  const { peutDeposer } = useAuth();

  // Fichiers sélectionnés par l'utilisateur
  const [fichiers, setFichiers]     = useState<File[]>([]);
  const [loading, setLoading]       = useState(false);
  // Résultats calculés depuis les CSV uploadés
  const [resultats, setResultats]   = useState<ReactiviteIndicateur[] | null>(null);
  // Résultats en base (fallback quand aucun CSV uploadé)
  const [baseData, setBaseData]     = useState<ReactiviteIndicateur[] | null>(null);
  const [baseLoading, setBaseLoading] = useState(false);

  // Chargement des données en base au montage
  React.useEffect(() => {
    setBaseLoading(true);
    getReactivite()
      .then(setBaseData)
      .catch(() => setBaseData([]))
      .finally(() => setBaseLoading(false));
  }, []);

  const lancer = async () => {
    if (fichiers.length === 0) { toast.error('Sélectionnez au moins un fichier CSV.'); return; }
    setLoading(true);
    try {
      const res = await calculerReactivite(fichiers);
      if (res.length === 0) {
        toast.error(
          'Aucun commercial identifié dans les fichiers. ' +
          'Vérifiez que les aliases sont configurés dans Administration.'
        );
      } else {
        setResultats(res);
        toast.success(`Réactivité calculée pour ${res.length} commercial(aux).`);
      }
    } catch (err) {
      toast.error(`Erreur : ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  // Données à afficher : calcul depuis CSV en priorité, base en fallback
  const lignes: ReactiviteIndicateur[] = resultats ?? baseData ?? [];
  const chargement = loading || (baseLoading && !baseData);

  const exporter = () => {
    exporterExcel('reactivite-commerciale', [
      {
        nom: 'Synthèse réseau',
        lignes: [{
          'Transactions analysées': somme(lignes.map((l) => l.nbTransactions)),
          'Tx / jour moyen': Number((somme(lignes.map((l) => l.txParJour)) / (lignes.length || 1)).toFixed(1)),
          Commerciaux: lignes.length,
        }],
      },
      {
        nom: 'Par commercial',
        lignes: lignes.map((l) => ({
          Commercial:                l.dsmName,
          'Nb transactions':         l.nbTransactions,
          'Jours actifs':            l.joursActifs,
          'Tx / jour':               l.txParJour,
          'Clients / jour':          l.clientsParJour,
          'Temps mort médian (min)': l.tempsMortMedian ?? 'N/A',
          'Temps mort max (min)':    l.tempsMortMax    ?? 'N/A',
          'Recharge médiane (min)':  l.tempsRechargeMedian ?? 'N/A',
          'Recharge min (min)':      l.tempsRechargeMin    ?? 'N/A',
        })),
      },
    ]);
    toast.success('Export téléchargé.');
  };

  return (
    <div>
      <PageHeader
        titre="Réactivité Commerciale"
        description="Rythme de travail depuis les CSV bruts MTN : cadence, clients touchés, temps morts et temps de recharge."
        actions={
          <Button icone={<DownloadIcon className="h-4 w-4" />} onClick={exporter} disabled={lignes.length === 0}>
            Exporter
          </Button>
        }
      />

      <div className="space-y-6">
        {/* ── Zone d'upload ── */}
        {peutDeposer && (
          <Section
            titre="Dépôt des CSV bruts"
            description="Chaque fichier est analysé côté serveur : l'alias configuré en base identifie automatiquement le commercial."
          >
            <p className="text-xs text-albarka-muted mb-3">
              Format attendu : CSV MTN avec colonnes <code>Date</code>, <code>From name</code>,{' '}
              <code>To name</code>, <code>Amount</code>, <code>Balance</code> et horodatage complet.
              Ex : <code>STEPHANE(7).csv</code>, <code>PARF-1-14.csv</code>.
            </p>

            <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-albarka-black transition-colors bg-gray-50">
              <UploadCloudIcon className="h-6 w-6 text-gray-400 mb-1" />
              <span className="text-sm text-gray-500">
                {fichiers.length > 0
                  ? `${fichiers.length} fichier(s) sélectionné(s)`
                  : 'Cliquez pour sélectionner les CSV bruts MTN'}
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
              {loading ? 'Calcul en cours…' : 'Calculer la réactivité'}
            </Button>

            {resultats && (
              <p className="mt-2 text-xs text-green-700">
                Résultats calculés depuis les CSV uploadés.{' '}
                <button
                  className="underline"
                  onClick={() => { setResultats(null); setFichiers([]); }}
                >
                  Effacer et revenir aux données en base
                </button>
              </p>
            )}
          </Section>
        )}

        {/* ── Résultats ── */}
        {chargement ? (
          <Squelette lignes={8} />
        ) : lignes.length === 0 ? (
          <EtatVide
            titre="Aucune donnée disponible"
            message="Importez des fichiers CSV bruts MTN pour calculer les indicateurs de réactivité."
          />
        ) : (
          <>
            {/* Métriques réseau */}
            <Section
              titre="Synthèse réseau"
              description="Moyennes calculées sur les commerciaux disposant de données exploitables."
            >
              <GrilleMetriques colonnes={4}>
                <MetricCard
                  libelle="Transactions analysées"
                  valeur={formatNombre(somme(lignes.map((l) => l.nbTransactions)))}
                  principale
                />
                <MetricCard
                  libelle="Tx / jour moyen"
                  valeur={formatNombre(somme(lignes.map((l) => l.txParJour)) / lignes.length)}
                />
                <MetricCard
                  libelle="Clients / jour moyen"
                  valeur={formatNombre(somme(lignes.map((l) => l.clientsParJour)) / lignes.length)}
                />
                <MetricCard
                  libelle="Temps mort médian réseau"
                  valeur={formatMinutes(
                    somme(lignes.map((l) => l.tempsMortMedian ?? 0)) /
                    (lignes.filter((l) => l.tempsMortMedian !== null).length || 1)
                  )}
                />
              </GrilleMetriques>
            </Section>

            {/* Tableau + graphiques via onglets */}
            <Tabs
              onglets={[
                {
                  id: 'tableau',
                  libelle: 'Tableau',
                  contenu: (
                    <Section
                      titre="Indicateurs par commercial"
                      description="« N/A » signale un indicateur non calculable (données insuffisantes ou Balance absente)."
                    >
                      <DataTable
                        colonnes={[
                          { cle: 'dsmName',        entete: 'Commercial' },
                          { cle: 'nbTransactions', entete: 'Nb tx',       numerique: true },
                          { cle: 'joursActifs',    entete: 'Jours actifs', numerique: true },
                          { cle: 'txParJour',      entete: 'Tx / jour',   numerique: true },
                          { cle: 'clientsParJour', entete: 'Clients / j', numerique: true },
                          {
                            cle: 'tempsMortMedian',
                            entete: 'Temps mort médian',
                            numerique: true,
                            rendu: (l) => formatMinutes(l.tempsMortMedian),
                          },
                          {
                            cle: 'tempsMortMax',
                            entete: 'Temps mort max',
                            numerique: true,
                            rendu: (l) => formatMinutes(l.tempsMortMax),
                          },
                          {
                            cle: 'tempsRechargeMedian',
                            entete: 'Recharge médiane',
                            numerique: true,
                            rendu: (l) => formatMinutes(l.tempsRechargeMedian),
                          },
                          {
                            cle: 'tempsRechargeMin',
                            entete: 'Recharge min',
                            numerique: true,
                            rendu: (l) => formatMinutes(l.tempsRechargeMin),
                          },
                        ]}
                        lignes={lignes}
                        cleLigne={(l) => `reac-${l.commercialId}`}
                        parPage={12}
                      />
                    </Section>
                  ),
                },
                {
                  id: 'tx-jour',
                  libelle: 'Tx / jour',
                  contenu: (
                    <Section titre="Transactions par jour — par commercial">
                      <GraphiqueIndicateur lignes={lignes} cle="txParJour" titre="Tx / jour" />
                    </Section>
                  ),
                },
                {
                  id: 'clients-jour',
                  libelle: 'Clients / jour',
                  contenu: (
                    <Section titre="Clients touchés par jour — par commercial">
                      <GraphiqueIndicateur lignes={lignes} cle="clientsParJour" titre="Clients / jour" />
                    </Section>
                  ),
                },
                {
                  id: 'temps-mort',
                  libelle: 'Temps mort',
                  contenu: (
                    <Section
                      titre="Temps mort médian (minutes)"
                      description="Écart médian entre deux transactions consécutives le même jour."
                    >
                      <GraphiqueIndicateur lignes={lignes} cle="tempsMortMedian" titre="Temps mort médian (min)" />
                    </Section>
                  ),
                },
                {
                  id: 'recharge',
                  libelle: 'Recharge',
                  contenu: (
                    <Section
                      titre="Temps de recharge médian (minutes)"
                      description="Durée médiane pour repasser au-dessus de 100 000 FCFA de balance."
                    >
                      <GraphiqueIndicateur lignes={lignes} cle="tempsRechargeMedian" titre="Recharge médiane (min)" />
                    </Section>
                  ),
                },
              ]}
            />
          </>
        )}
      </div>
    </div>
  );
}
