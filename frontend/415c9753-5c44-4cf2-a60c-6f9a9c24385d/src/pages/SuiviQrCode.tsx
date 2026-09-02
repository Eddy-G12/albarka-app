import React, { useState } from 'react';
import { toast } from 'sonner';
import { FileCheck2Icon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Section, TitreBloc } from '../components/ui/Section';
import { FileDropzone } from '../components/FileDropzone';
import { Button } from '../components/ui/Button';
import { Champ, Input } from '../components/ui/Field';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { DataTable } from '../components/DataTable';
import { StatusBadge } from '../components/StatusBadge';
import { BlocAsync, EtatVide, Squelette } from '../components/ui/States';
import { useAsync } from '../hooks/useAsync';
import { getRepartitionQr } from '../services/qr';
import { DATE_QR_COURANTE } from '../data/seed';
import { formatNombre, formatPourcent, labelDate } from '../utils/format';
import { exporterExcel } from '../utils/export';
import { LIBELLE_STATUT } from '../utils/business';

export function SuiviQrCode() {
  const [dateRef, setDateRef] = useState(DATE_QR_COURANTE);
  const [traite, setTraite] = useState(false);
  const apercu = useAsync(() => getRepartitionQr(DATE_QR_COURANTE), []);

  return (
    <div>
      <PageHeader
        titre="Suivi QR Code"
        description="Dépôt du fichier QR, classification des agents selon les 4 statuts et génération du rapport Excel multi-onglets." />
      

      <div className="space-y-6">
        <Section
          titre="Dépôt du fichier"
          description="Format .xlsx ou .gz. Le format compressé est reconnu par sa signature binaire (0x1f 0x8b)."
          actions={
          <Champ label="Date de référence" htmlFor="date-ref" className="w-44">
              <Input
              id="date-ref"
              type="date"
              value={dateRef}
              onChange={(e) => setDateRef(e.target.value)} />
            
            </Champ>
          }>
          
          <FileDropzone
            accept=".xlsx,.gz"
            multiple={false}
            legende="Colonnes attendues : active_deployed, active_30, last_qr_co_date, segment_group, dsm_name, pos_name, pos_msisdn."
            onTermine={() => {
              setTraite(true);
              toast.success('Fichier classifié — rapport disponible ci-dessous.');
            }} />
          
          <div className="mt-4 rounded-md border border-albarka-border bg-albarka-bg px-4 py-3">
            <TitreBloc>Ordre de classification appliqué</TitreBloc>
            <ol className="list-decimal space-y-1 pl-5 text-xs text-albarka-muted">
              <li>
                <code>active_deployed</code> vide → <strong>Sans QR Code</strong>
              </li>
              <li>
                <code>active_30 == 0</code> → <strong>QR non utilisé (+30j)</strong>
              </li>
              <li>
                <code>date_ref − last_qr_co_date ≥ 20 jours</code> → <strong>Risque inactivité</strong>
              </li>
              <li>
                sinon → <strong>Actif</strong>
              </li>
            </ol>
          </div>
        </Section>

        <Section
          titre="Résultat de la classification"
          description={
          traite ?
          `Rapport généré pour le ${labelDate(dateRef)} et historisé dans la base.` :
          'Aperçu du dernier fichier traité, en attendant un nouveau dépôt.'
          }>
          
          <BlocAsync etat={apercu} squelette={<Squelette lignes={6} />}>
            {({ agents, repartition }) =>
            agents.length === 0 ?
            <EtatVide
              titre="Aucun fichier traité"
              message="Déposez un fichier QR Code pour lancer la classification des agents." /> :


            <div className="space-y-5">
                  <GrilleMetriques colonnes={5}>
                    <MetricCard
                  libelle="Agents traités"
                  valeur={formatNombre(repartition.total)}
                  principale />
                
                    <MetricCard
                  libelle="Sans QR Code"
                  valeur={formatNombre(repartition.parStatut.sans_qr)}
                  detail={formatPourcent(repartition.tauxSansQr)} />
                
                    <MetricCard
                  libelle="QR non utilisé"
                  valeur={formatNombre(repartition.parStatut.non_utilise)}
                  detail={formatPourcent(repartition.tauxNonUtilises)} />
                
                    <MetricCard
                  libelle="Risque inactivité"
                  valeur={formatNombre(repartition.parStatut.risque)}
                  detail={formatPourcent(repartition.tauxRisque)} />
                
                    <MetricCard
                  libelle="Actifs"
                  valeur={formatNombre(repartition.parStatut.actif)}
                  detail={formatPourcent(repartition.tauxUtilisation)} />
                
                  </GrilleMetriques>

                  <DataTable
                colonnes={[
                { cle: 'posName', entete: 'Agent' },
                { cle: 'posMsisdn', entete: 'MSISDN' },
                { cle: 'dsmName', entete: 'DSM' },
                { cle: 'segmentGroup', entete: 'Segment' },
                {
                  cle: 'lastQrCoDate',
                  entete: 'Dernière connexion QR',
                  rendu: (a) => a.lastQrCoDate ? labelDate(a.lastQrCoDate) : '—'
                },
                {
                  cle: 'statut',
                  entete: 'Statut',
                  rendu: (a) => <StatusBadge statut={a.statut} />
                }]
                }
                lignes={agents}
                cleLigne={(a) => a.posMsisdn}
                recherche
                parPage={12}
                compact />
              

                  <Button
                variante="primaire"
                icone={<FileCheck2Icon className="h-4 w-4" />}
                onClick={() => {
                  exporterExcel(`rapport-qr-${dateRef}`, [
                  {
                    nom: 'Résumé',
                    lignes: Object.entries(repartition.parStatut).map(([statut, nb]) => ({
                      Statut: LIBELLE_STATUT[statut as keyof typeof LIBELLE_STATUT],
                      Agents: nb,
                      'Part (%)': Number((nb / (repartition.total || 1) * 100).toFixed(2))
                    }))
                  },
                  ...(['sans_qr', 'non_utilise', 'risque'] as const).map((statut) => ({
                    nom: LIBELLE_STATUT[statut].slice(0, 28),
                    lignes: agents.
                    filter((a) => a.statut === statut).
                    map((a) => ({
                      Agent: a.posName,
                      MSISDN: a.posMsisdn,
                      DSM: a.dsmName,
                      Segment: a.segmentGroup,
                      Ville: a.town
                    }))
                  }))]
                  );
                  toast.success('Rapport Excel téléchargé.');
                }}>
                
                    Générer le rapport multi-onglets
                  </Button>
                </div>

            }
          </BlocAsync>
        </Section>
      </div>
    </div>);

}