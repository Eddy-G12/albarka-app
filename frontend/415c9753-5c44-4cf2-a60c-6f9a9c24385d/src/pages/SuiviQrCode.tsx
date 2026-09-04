import React, { useState } from 'react';
import { toast } from 'sonner';
import { UploadCloudIcon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Section, TitreBloc } from '../components/ui/Section';
import { Button } from '../components/ui/Button';
import { Champ, Input } from '../components/ui/Field';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { DataTable } from '../components/DataTable';
import { StatusBadge } from '../components/StatusBadge';
import { BlocAsync, EtatVide, Squelette } from '../components/ui/States';
import { useAsync } from '../hooks/useAsync';
import { getRepartitionQr, getDatesQr } from '../services/qr';
import { importerQr, type ResultatImportQr } from '../services/import';
import { formatNombre, formatPourcent, labelDate } from '../utils/format';

export function SuiviQrCode() {
  const [fichier, setFichier]         = useState<File | null>(null);
  const [dateRef, setDateRef]         = useState('');
  const [loading, setLoading]         = useState(false);
  const [resultat, setResultat]       = useState<ResultatImportQr | null>(null);

  const datesDisponibles = useAsync(() => getDatesQr(), []);
  const derniereDate = datesDisponibles.donnees?.[0];

  const apercu = useAsync(
    () => derniereDate ? getRepartitionQr(derniereDate) : Promise.resolve(null),
    [derniereDate],
  );

  const lancer = async () => {
    if (!fichier) { toast.error('Sélectionnez un fichier.'); return; }
    setLoading(true);
    try {
      const res = await importerQr(fichier, dateRef || undefined);
      setResultat(res);
      toast.success(`${res.nb_agents} agents classifiés — ${res.date_ref}`);
    } catch (err) {
      toast.error(`Erreur : ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        titre="Suivi QR Code"
        description="Dépôt du fichier QR, classification des agents et génération du rapport Excel." />

      <div className="space-y-6">
        {/* ── Zone d'import ── */}
        <Section
          titre="Dépôt du fichier"
          description="Format .xlsx ou .gz. La date de référence est détectée automatiquement depuis le nom du fichier."
          actions={
            <Champ label="Date de référence" htmlFor="date-ref" className="w-44">
              <Input
                id="date-ref"
                type="date"
                value={dateRef}
                onChange={(e) => setDateRef(e.target.value)}
              />
            </Champ>
          }
        >
          <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-albarka-black transition-colors bg-gray-50">
            <UploadCloudIcon className="h-6 w-6 text-gray-400 mb-1" />
            <span className="text-sm text-gray-500">
              {fichier ? fichier.name : 'Cliquez pour sélectionner un fichier QR Code (.xlsx ou .gz)'}
            </span>
            <input
              type="file"
              accept=".xlsx,.gz"
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
            {loading ? 'Classification en cours…' : 'Générer le rapport'}
          </Button>

          {/* Règles de classification */}
          <div className="mt-4 rounded-md border border-albarka-border bg-albarka-bg px-4 py-3">
            <TitreBloc>Ordre de classification appliqué</TitreBloc>
            <ol className="list-decimal space-y-1 pl-5 text-xs text-albarka-muted">
              <li><code>active_deployed</code> vide → <strong>Sans QR Code</strong></li>
              <li><code>active_30 == 0</code> → <strong>QR non utilisé (+30j)</strong></li>
              <li><code>date_ref − last_qr_co_date ≥ 20 jours</code> → <strong>Risque inactivité</strong></li>
              <li>sinon → <strong>Actif</strong></li>
            </ol>
          </div>
        </Section>

        {/* ── Résultat du dernier import ── */}
        {resultat && (
          <Section titre={`Résultat — ${resultat.date_ref}`}>
            <GrilleMetriques colonnes={5}>
              <MetricCard libelle="Agents traités"   valeur={formatNombre(resultat.nb_agents)}   principale />
              <MetricCard libelle="Sans QR Code"     valeur={formatNombre(resultat.sans_qr)}     />
              <MetricCard libelle="QR non utilisé"   valeur={formatNombre(resultat.non_utilise)} />
              <MetricCard libelle="Risque inactivité" valeur={formatNombre(resultat.risque)}     />
              <MetricCard libelle="Actifs"            valeur={formatNombre(resultat.actif)}      />
            </GrilleMetriques>
          </Section>
        )}

        {/* ── Aperçu dernière date en base ── */}
        <Section
          titre="Aperçu du dernier fichier traité"
          description={derniereDate ? `Date en base : ${labelDate(derniereDate)}` : 'Aucun fichier traité pour l\'instant.'}
        >
          <BlocAsync etat={apercu} squelette={<Squelette lignes={6} />}>
            {(data) =>
              !data || data.agents.length === 0 ? (
                <EtatVide
                  titre="Aucun fichier traité"
                  message="Déposez un fichier QR Code pour lancer la classification."
                />
              ) : (
                <div className="space-y-5">
                  <GrilleMetriques colonnes={5}>
                    <MetricCard libelle="Agents"         valeur={formatNombre(data.repartition.total)}                  principale />
                    <MetricCard libelle="Sans QR"        valeur={formatNombre(data.repartition.parStatut.sans_qr)}
                                detail={formatPourcent(data.repartition.tauxSansQr)} />
                    <MetricCard libelle="Non utilisé"    valeur={formatNombre(data.repartition.parStatut.non_utilise)}
                                detail={formatPourcent(data.repartition.tauxNonUtilises)} />
                    <MetricCard libelle="Risque"         valeur={formatNombre(data.repartition.parStatut.risque)}
                                detail={formatPourcent(data.repartition.tauxRisque)} />
                    <MetricCard libelle="Actifs"         valeur={formatNombre(data.repartition.parStatut.actif)}
                                detail={formatPourcent(data.repartition.tauxUtilisation)} />
                  </GrilleMetriques>

                  <DataTable
                    colonnes={[
                      { cle: 'posName',      entete: 'Agent'    },
                      { cle: 'posMsisdn',    entete: 'MSISDN'   },
                      { cle: 'dsmName',      entete: 'DSM'      },
                      { cle: 'segmentGroup', entete: 'Segment'  },
                      {
                        cle: 'lastQrCoDate',
                        entete: 'Dernière connexion',
                        rendu: (a) => a.lastQrCoDate ? labelDate(a.lastQrCoDate) : '—',
                      },
                      { cle: 'statut', entete: 'Statut', rendu: (a) => <StatusBadge statut={a.statut} /> },
                    ]}
                    lignes={data.agents}
                    cleLigne={(a) => a.posMsisdn}
                    recherche
                    parPage={12}
                    compact
                  />
                </div>
              )
            }
          </BlocAsync>
        </Section>
      </div>
    </div>
  );
}
