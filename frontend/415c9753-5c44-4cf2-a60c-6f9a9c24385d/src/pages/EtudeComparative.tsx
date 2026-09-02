import React, { useEffect, useState } from 'react';
import { DownloadIcon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Section, TitreBloc } from '../components/ui/Section';
import { SelecteurDateQr } from '../components/Filtres';
import { Button } from '../components/ui/Button';
import { DataTable } from '../components/DataTable';
import { StatusBadge } from '../components/StatusBadge';
import { BarresGroupees } from '../components/charts/Charts';
import { BlocAsync, Squelette } from '../components/ui/States';
import { FileDropzone } from '../components/FileDropzone';
import { useAuth } from '../contexts/AuthContext';
import { useAsync } from '../hooks/useAsync';
import { getComparaisonQr, getDatesQr } from '../services/qr';
import { DATES_QR } from '../data/seed';
import { LIBELLE_STATUT, ORDRE_STATUTS } from '../utils/business';
import { formatPourcent, labelDate } from '../utils/format';
import { exporterExcel } from '../utils/export';

export function EtudeComparative() {
  const { peutDeposer } = useAuth();
  const [datesDisponibles, setDatesDisponibles] = useState<string[]>(DATES_QR);
  const [dateA, setDateA] = useState(DATES_QR[DATES_QR.length - 2]);
  const [dateB, setDateB] = useState(DATES_QR[DATES_QR.length - 1]);
  const comparaison = useAsync(() => getComparaisonQr(dateA, dateB), [dateA, dateB]);

  useEffect(() => {
    getDatesQr().then((dates) => {
      if (dates.length >= 2) {
        setDatesDisponibles(dates);
        setDateA(dates[1]); // avant-dernière
        setDateB(dates[0]); // dernière
      } else if (dates.length === 1) {
        setDatesDisponibles(dates);
        setDateB(dates[0]);
      }
    }).catch(() => {});
  }, []);

  return (
    <div>
      <PageHeader
        titre="Étude Comparative"
        description="Comparez deux dates de référence QR Code déjà traitées et suivez les agents qui ont changé de statut."
        filtres={
        <>
            <SelecteurDateQr
            label="Date de départ"
            valeur={dateA}
            onChange={setDateA}
            id="date-a"
            dates={datesDisponibles.filter((d) => d !== dateB)} />
          
            <SelecteurDateQr
            label="Date d'arrivée"
            valeur={dateB}
            onChange={setDateB}
            id="date-b"
            dates={datesDisponibles.filter((d) => d !== dateA)} />
          
          </>
        } />
      

      <div className="space-y-6">
        {peutDeposer &&
        <Section
          titre="Comparer deux nouveaux fichiers"
          description="Si l'une des dates n'a pas encore été traitée, déposez les deux fichiers QR Code ici.">
          
            <FileDropzone
            accept=".xlsx,.gz"
            legende="Deux fichiers QR Code (.xlsx ou .gz). Le format compressé est reconnu par sa signature binaire." />
          
          </Section>
        }

        <BlocAsync etat={comparaison} squelette={<Squelette lignes={8} />}>
          {(donnees) => {
            const resume = ORDRE_STATUTS.map((statut) => ({
              statut,
              libelle: LIBELLE_STATUT[statut],
              avant: donnees.repartitionA.parStatut[statut],
              apres: donnees.repartitionB.parStatut[statut],
              partAvant: donnees.repartitionA.parStatut[statut] / (donnees.repartitionA.total || 1) * 100,
              partApres: donnees.repartitionB.parStatut[statut] / (donnees.repartitionB.total || 1) * 100
            }));

            return (
              <>
                <Section
                  titre="Résumé comparatif"
                  description={`${labelDate(dateA)} → ${labelDate(dateB)}`}
                  actions={
                  <Button
                    icone={<DownloadIcon className="h-4 w-4" />}
                    onClick={() =>
                    exporterExcel(`comparatif-${dateA}_${dateB}`, [
                    {
                      nom: 'Résumé comparatif',
                      lignes: resume.map((l) => ({
                        Statut: l.libelle,
                        [labelDate(dateA)]: l.avant,
                        [labelDate(dateB)]: l.apres,
                        Évolution: l.apres - l.avant
                      }))
                    },
                    {
                      nom: 'Par catégorie',
                      lignes: donnees.parSegment.map((s) => ({
                        Segment: s.segment,
                        [labelDate(dateA)]: s.avant,
                        [labelDate(dateB)]: s.apres
                      }))
                    },
                    {
                      nom: 'Mouvements',
                      lignes: donnees.mouvements.map((m) => ({
                        Agent: m.posName,
                        MSISDN: m.posMsisdn,
                        DSM: m.dsmName,
                        Segment: m.segmentGroup,
                        Avant: LIBELLE_STATUT[m.statutAvant],
                        Après: LIBELLE_STATUT[m.statutApres]
                      }))
                    }]
                    )
                    }>
                    
                      Exporter
                    </Button>
                  }>
                  
                  <DataTable
                    colonnes={[
                    { cle: 'libelle', entete: 'Statut' },
                    { cle: 'avant', entete: labelDate(dateA), numerique: true },
                    {
                      cle: 'partAvant',
                      entete: 'Part',
                      numerique: true,
                      rendu: (l) => formatPourcent(l.partAvant)
                    },
                    { cle: 'apres', entete: labelDate(dateB), numerique: true },
                    {
                      cle: 'partApres',
                      entete: 'Part',
                      numerique: true,
                      rendu: (l) => formatPourcent(l.partApres)
                    },
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
                    lignes={resume}
                    cleLigne={(l) => l.statut}
                    parPage={4}
                    compact />
                  
                </Section>

                <Section titre="Répartition par catégorie">
                  <BarresGroupees
                    donnees={donnees.parSegment.map((s) => ({
                      segment: s.segment,
                      avant: s.avant,
                      apres: s.apres
                    }))}
                    cleLabel="segment"
                    monetaire={false}
                    series={[
                    { cle: 'avant', nom: labelDate(dateA), couleur: '#6B7280' },
                    { cle: 'apres', nom: labelDate(dateB), couleur: '#F5A623' }]
                    } />
                  
                </Section>

                <Section
                  titre="Mouvements détaillés"
                  description={`${donnees.mouvements.length} agents ont changé de statut, rapprochés par pos_msisdn.`}>
                  
                  <TitreBloc>Changements de statut</TitreBloc>
                  <DataTable
                    colonnes={[
                    { cle: 'posName', entete: 'Agent' },
                    { cle: 'posMsisdn', entete: 'MSISDN' },
                    { cle: 'dsmName', entete: 'DSM' },
                    { cle: 'segmentGroup', entete: 'Segment' },
                    {
                      cle: 'statutAvant',
                      entete: 'Avant',
                      rendu: (m) => <StatusBadge statut={m.statutAvant} />
                    },
                    {
                      cle: 'statutApres',
                      entete: 'Après',
                      rendu: (m) => <StatusBadge statut={m.statutApres} />
                    }]
                    }
                    lignes={donnees.mouvements}
                    cleLigne={(m) => m.posMsisdn}
                    recherche
                    parPage={12}
                    compact />
                  
                </Section>
              </>);

          }}
        </BlocAsync>
      </div>
    </div>);

}