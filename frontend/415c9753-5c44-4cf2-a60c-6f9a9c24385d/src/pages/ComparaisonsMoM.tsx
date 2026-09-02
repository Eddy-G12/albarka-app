import React, { useEffect, useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Tabs } from '../components/ui/Tabs';
import { Section, TitreBloc } from '../components/ui/Section';
import { SelecteurDateQr, SelecteurMois } from '../components/Filtres';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { DataTable } from '../components/DataTable';
import { BlocAsync, Squelette } from '../components/ui/States';
import { useAuth } from '../contexts/AuthContext';
import { useAsync } from '../hooks/useAsync';
import { getApproMoM, getCashMoM } from '../services/cash';
import { getComparaisonQr, getDatesQr } from '../services/qr';
import { DATES_QR, MOIS_COURANT } from '../data/seed';
import { LIBELLE_STATUT, ORDRE_STATUTS, somme } from '../utils/business';
import {
  evolutionPct,
  formatFcfa,
  formatPourcent,
  labelDate,
  labelMois } from
'../utils/format';
import { exporterExcel } from '../utils/export';

function CelluleEvolution({ valeur, monetaire = true }: {valeur: number;monetaire?: boolean;}) {
  const couleur =
  valeur > 0 ? 'text-statut-actif' : valeur < 0 ? 'text-[#C0392B]' : 'text-albarka-muted';
  return (
    <span className={couleur}>
      {valeur > 0 ? '+' : ''}
      {monetaire ? formatFcfa(valeur) : formatPourcent(valeur)}
    </span>);

}

function OngletCash({ commercialId }: {commercialId?: number;}) {
  const [mois, setMois] = useState(MOIS_COURANT);
  const cash = useAsync(() => getCashMoM(mois, commercialId), [mois, commercialId]);

  return (
    <Section
      titre="Cash In / Cash Out mois vs mois-1"
      description="Le mois précédent est déduit automatiquement du mois de référence."
      actions={<SelecteurMois valeur={mois} onChange={setMois} id="mois-mom-cash" />}>
      
      <BlocAsync etat={cash} squelette={<Squelette lignes={7} />}>
        {(donnees) => {
          const totalIn = somme(donnees.lignes.map((l) => l.cashIn));
          const totalInAvant = somme(donnees.lignes.map((l) => l.cashInPrecedent));
          const totalOut = somme(donnees.lignes.map((l) => l.cashOut));
          const totalOutAvant = somme(donnees.lignes.map((l) => l.cashOutPrecedent));

          return (
            <div className="space-y-5">
              <GrilleMetriques colonnes={4}>
                <MetricCard
                  libelle={`Cash In ${labelMois(donnees.mois)}`}
                  valeur={formatFcfa(totalIn, true)}
                  unite="FCFA"
                  principale
                  delta={totalIn - totalInAvant}
                  deltaLabel={formatPourcent(evolutionPct(totalIn, totalInAvant))} />
                
                <MetricCard
                  libelle={`Cash In ${labelMois(donnees.precedent)}`}
                  valeur={formatFcfa(totalInAvant, true)}
                  unite="FCFA" />
                
                <MetricCard
                  libelle={`Cash Out ${labelMois(donnees.mois)}`}
                  valeur={formatFcfa(totalOut, true)}
                  unite="FCFA"
                  delta={totalOut - totalOutAvant}
                  deltaLabel={formatPourcent(evolutionPct(totalOut, totalOutAvant))} />
                
                <MetricCard
                  libelle={`Cash Out ${labelMois(donnees.precedent)}`}
                  valeur={formatFcfa(totalOutAvant, true)}
                  unite="FCFA" />
                
              </GrilleMetriques>

              <DataTable
                colonnes={[
                { cle: 'dsmName', entete: 'Commercial' },
                {
                  cle: 'cashInPrecedent',
                  entete: `CI ${labelMois(donnees.precedent)}`,
                  numerique: true,
                  rendu: (l) => formatFcfa(l.cashInPrecedent)
                },
                {
                  cle: 'cashIn',
                  entete: `CI ${labelMois(donnees.mois)}`,
                  numerique: true,
                  rendu: (l) => formatFcfa(l.cashIn)
                },
                {
                  cle: 'evolIn',
                  entete: 'Évol. CI',
                  numerique: true,
                  valeur: (l) => l.cashIn - l.cashInPrecedent,
                  rendu: (l) => <CelluleEvolution valeur={l.cashIn - l.cashInPrecedent} />
                },
                {
                  cle: 'evolInPct',
                  entete: 'Évol. %',
                  numerique: true,
                  valeur: (l) => evolutionPct(l.cashIn, l.cashInPrecedent),
                  rendu: (l) =>
                  <CelluleEvolution
                    valeur={evolutionPct(l.cashIn, l.cashInPrecedent)}
                    monetaire={false} />


                },
                {
                  cle: 'cashOut',
                  entete: `CO ${labelMois(donnees.mois)}`,
                  numerique: true,
                  rendu: (l) => formatFcfa(l.cashOut)
                },
                {
                  cle: 'evolOut',
                  entete: 'Évol. CO',
                  numerique: true,
                  valeur: (l) => l.cashOut - l.cashOutPrecedent,
                  rendu: (l) => <CelluleEvolution valeur={l.cashOut - l.cashOutPrecedent} />
                }]
                }
                lignes={donnees.lignes}
                cleLigne={(l) => `mom-${l.commercialId}`}
                parPage={12}
                onExport={() =>
                exporterExcel(`mom-cash-${donnees.mois}`, [
                {
                  nom: 'Cash MoM',
                  lignes: donnees.lignes.map((l) => ({
                    Commercial: l.dsmName,
                    [`CI ${donnees.precedent}`]: l.cashInPrecedent,
                    [`CI ${donnees.mois}`]: l.cashIn,
                    'Évolution CI': l.cashIn - l.cashInPrecedent,
                    [`CO ${donnees.precedent}`]: l.cashOutPrecedent,
                    [`CO ${donnees.mois}`]: l.cashOut,
                    'Évolution CO': l.cashOut - l.cashOutPrecedent
                  }))
                }]
                )
                } />
              
            </div>);

        }}
      </BlocAsync>
    </Section>);

}

function OngletAppro({ commercialId }: {commercialId?: number;}) {
  const [mois, setMois] = useState(MOIS_COURANT);
  const appro = useAsync(() => getApproMoM(mois, commercialId), [mois, commercialId]);

  return (
    <Section
      titre="Appro / Destockage mois vs mois-1"
      actions={<SelecteurMois valeur={mois} onChange={setMois} id="mois-mom-appro" />}>
      
      <BlocAsync etat={appro} squelette={<Squelette lignes={6} />}>
        {(donnees) => {
          const totalAppro = somme(donnees.lignes.map((l) => l.appro));
          const totalApproAvant = somme(donnees.lignes.map((l) => l.apprPrecedent));
          const totalDestoc = somme(donnees.lignes.map((l) => l.destockage));
          const totalDestocAvant = somme(donnees.lignes.map((l) => l.destocPrecedent));

          return (
            <div className="space-y-5">
              <GrilleMetriques colonnes={4}>
                <MetricCard
                  libelle={`Appros ${labelMois(donnees.mois)}`}
                  valeur={formatFcfa(totalAppro, true)}
                  unite="FCFA"
                  principale
                  delta={totalAppro - totalApproAvant}
                  deltaLabel={formatPourcent(evolutionPct(totalAppro, totalApproAvant))} />
                
                <MetricCard
                  libelle={`Appros ${labelMois(donnees.precedent)}`}
                  valeur={formatFcfa(totalApproAvant, true)}
                  unite="FCFA" />
                
                <MetricCard
                  libelle={`Destockages ${labelMois(donnees.mois)}`}
                  valeur={formatFcfa(totalDestoc, true)}
                  unite="FCFA"
                  delta={totalDestoc - totalDestocAvant}
                  deltaLabel={formatPourcent(evolutionPct(totalDestoc, totalDestocAvant))} />
                
                <MetricCard
                  libelle={`Destockages ${labelMois(donnees.precedent)}`}
                  valeur={formatFcfa(totalDestocAvant, true)}
                  unite="FCFA" />
                
              </GrilleMetriques>

              <DataTable
                colonnes={[
                { cle: 'dsmName', entete: 'Commercial' },
                {
                  cle: 'apprPrecedent',
                  entete: `Appro ${labelMois(donnees.precedent)}`,
                  numerique: true,
                  rendu: (l) => formatFcfa(l.apprPrecedent)
                },
                {
                  cle: 'appro',
                  entete: `Appro ${labelMois(donnees.mois)}`,
                  numerique: true,
                  rendu: (l) => formatFcfa(l.appro)
                },
                {
                  cle: 'evolAppro',
                  entete: 'Évol.',
                  numerique: true,
                  valeur: (l) => l.appro - l.apprPrecedent,
                  rendu: (l) => <CelluleEvolution valeur={l.appro - l.apprPrecedent} />
                },
                {
                  cle: 'destockage',
                  entete: `Destoc. ${labelMois(donnees.mois)}`,
                  numerique: true,
                  rendu: (l) => formatFcfa(l.destockage)
                },
                {
                  cle: 'evolDestoc',
                  entete: 'Évol.',
                  numerique: true,
                  valeur: (l) => l.destockage - l.destocPrecedent,
                  rendu: (l) => <CelluleEvolution valeur={l.destockage - l.destocPrecedent} />
                }]
                }
                lignes={donnees.lignes}
                cleLigne={(l) => `mom-appro-${l.dsmName}`}
                parPage={12} />
              
            </div>);

        }}
      </BlocAsync>
    </Section>);

}

function OngletQr({ dsmName }: {dsmName?: string;}) {
  const [datesDisponibles, setDatesDisponibles] = useState<string[]>(DATES_QR);
  const [dateA, setDateA] = useState(DATES_QR[DATES_QR.length - 2]);
  const [dateB, setDateB] = useState(DATES_QR[DATES_QR.length - 1]);
  const comparaison = useAsync(() => getComparaisonQr(dateA, dateB), [dateA, dateB]);

  useEffect(() => {
    getDatesQr().then((dates) => {
      if (dates.length >= 2) {
        setDatesDisponibles(dates);
        setDateA(dates[1]);
        setDateB(dates[0]);
      } else if (dates.length === 1) {
        setDatesDisponibles(dates);
        setDateB(dates[0]);
      }
    }).catch(() => {});
  }, []);

  return (
    <Section
      titre="QR Code mois vs mois-1"
      description={dsmName ? `Périmètre ${dsmName}.` : 'Répartition réseau entre deux dates de référence.'}
      actions={
      <>
          <SelecteurDateQr
          label="Date M-1"
          valeur={dateA}
          onChange={setDateA}
          id="qr-mom-a"
          dates={datesDisponibles.filter((d) => d !== dateB)} />
        
          <SelecteurDateQr
          label="Date M"
          valeur={dateB}
          onChange={setDateB}
          id="qr-mom-b"
          dates={datesDisponibles.filter((d) => d !== dateA)} />
        
        </>
      }>
      
      <BlocAsync etat={comparaison} squelette={<Squelette lignes={6} />}>
        {(donnees) => {
          const lignes = ORDRE_STATUTS.map((statut) => ({
            statut,
            libelle: LIBELLE_STATUT[statut],
            avant: donnees.repartitionA.parStatut[statut],
            partAvant: donnees.repartitionA.parStatut[statut] / (donnees.repartitionA.total || 1) * 100,
            apres: donnees.repartitionB.parStatut[statut],
            partApres: donnees.repartitionB.parStatut[statut] / (donnees.repartitionB.total || 1) * 100
          }));

          return (
            <div className="space-y-5">
              <GrilleMetriques colonnes={4}>
                <MetricCard
                  libelle="Taux déploiement"
                  valeur={formatPourcent(donnees.repartitionB.tauxDeploiement)}
                  delta={donnees.repartitionB.tauxDeploiement - donnees.repartitionA.tauxDeploiement}
                  deltaLabel={formatPourcent(
                    donnees.repartitionB.tauxDeploiement - donnees.repartitionA.tauxDeploiement
                  )}
                  principale />
                
                <MetricCard
                  libelle="Taux actif"
                  valeur={formatPourcent(donnees.repartitionB.tauxUtilisation)}
                  delta={donnees.repartitionB.tauxUtilisation - donnees.repartitionA.tauxUtilisation}
                  deltaLabel={formatPourcent(
                    donnees.repartitionB.tauxUtilisation - donnees.repartitionA.tauxUtilisation
                  )} />
                
                <MetricCard
                  libelle="Taux risque"
                  valeur={formatPourcent(donnees.repartitionB.tauxRisque)} />
                
                <MetricCard
                  libelle="QR non utilisés"
                  valeur={formatPourcent(donnees.repartitionB.tauxNonUtilises)} />
                
              </GrilleMetriques>

              <div>
                <TitreBloc>Répartition par statut</TitreBloc>
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
                    rendu: (l) =>
                    <CelluleEvolution valeur={l.apres - l.avant} monetaire={false} />

                  }]
                  }
                  lignes={lignes}
                  cleLigne={(l) => l.statut}
                  parPage={4}
                  compact />
                
              </div>
            </div>);

        }}
      </BlocAsync>
    </Section>);

}

export function ComparaisonsMoM() {
  const { commercial, estCommercial } = useAuth();
  const commercialId = estCommercial ? commercial?.id : undefined;

  return (
    <div>
      <PageHeader
        titre="Comparaisons MoM"
        description={
        estCommercial ?
        'Vos évolutions mois par mois sur le cash, les appros et le QR Code.' :
        'Évolutions mois par mois du réseau sur le cash, les appros et le QR Code.'
        } />
      
      <Tabs
        onglets={[
        { id: 'cash', libelle: 'Cash In / Cash Out', contenu: <OngletCash commercialId={commercialId} /> },
        { id: 'appro', libelle: 'Appro / Destockage', contenu: <OngletAppro commercialId={commercialId} /> },
        { id: 'qr', libelle: 'QR Code', contenu: <OngletQr dsmName={commercial?.dsmName} /> }]
        } />
      
    </div>);

}