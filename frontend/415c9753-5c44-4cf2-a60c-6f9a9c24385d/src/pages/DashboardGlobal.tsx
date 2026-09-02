import React from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { SelecteurDateQr, SelecteurMois } from '../components/Filtres';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { BlocAsync, SqueletteCartes } from '../components/ui/States';
import { SectionCash } from '../components/dashboard/SectionCash';
import { SectionQr } from '../components/dashboard/SectionQr';
import { SectionAppro } from '../components/dashboard/SectionAppro';
import { SectionReactivite } from '../components/dashboard/SectionReactivite';
import { useFiltres } from '../contexts/FiltresContext';
import { useAsync } from '../hooks/useAsync';
import { approParCommercialSync, cashParCommercialSync } from '../services/cash';
import { getRepartitionQr } from '../services/qr';
import { somme } from '../utils/business';
import { formatFcfa, formatDelta, formatNombre, labelMois, moisPrecedent } from '../utils/format';

export function DashboardGlobal() {
  const { moisCash, moisAppro, dateQr, setMoisCash, setMoisAppro, setDateQr } = useFiltres();

  const synthese = useAsync(async () => {
    const cash = cashParCommercialSync(moisCash);
    const cashAvant = cashParCommercialSync(moisPrecedent(moisCash));
    const appro = approParCommercialSync(moisAppro);
    const { repartition } = await getRepartitionQr(dateQr);
    return {
      nbTransactions: somme(cash.map((l) => l.nbTransactions)),
      cashIn: somme(cash.map((l) => l.cashIn)),
      cashInAvant: somme(cashAvant.map((l) => l.cashIn)),
      cashOut: somme(cash.map((l) => l.cashOut)),
      cashOutAvant: somme(cashAvant.map((l) => l.cashOut)),
      agentsActifs: repartition.parStatut.actif,
      agentsTotal: repartition.total,
      montantAppros: somme(appro.map((l) => l.montantAppros)),
      montantDestockages: somme(appro.map((l) => l.montantDestockages))
    };
  }, [moisCash, moisAppro, dateQr]);

  return (
    <div>
      <PageHeader
        titre="Dashboard Global"
        description="Vue consolidée du réseau : cash, réactivité, couverture QR Code et mouvements de flotte."
        filtres={
        <>
            <SelecteurMois label="Mois cash" valeur={moisCash} onChange={setMoisCash} id="mois-cash" />
            <SelecteurMois
            label="Mois appro"
            valeur={moisAppro}
            onChange={setMoisAppro}
            id="mois-appro" />
          
            <SelecteurDateQr valeur={dateQr} onChange={setDateQr} />
          </>
        } />
      

      <div className="space-y-6">
        <BlocAsync etat={synthese} squelette={<SqueletteCartes nb={6} />}>
          {(s) =>
          <GrilleMetriques colonnes={6}>
              <MetricCard
              libelle="Transactions MoMo"
              valeur={formatNombre(s.nbTransactions)}
              detail={labelMois(moisCash)} />
            
              <MetricCard
              libelle="Cash In réseau"
              valeur={formatFcfa(s.cashIn, true)}
              unite="FCFA"
              principale
              delta={s.cashIn - s.cashInAvant}
              deltaLabel={`${formatDelta(s.cashIn - s.cashInAvant)} vs M-1`} />
            
              <MetricCard
              libelle="Cash Out réseau"
              valeur={formatFcfa(s.cashOut, true)}
              unite="FCFA"
              delta={s.cashOut - s.cashOutAvant}
              deltaLabel={`${formatDelta(s.cashOut - s.cashOutAvant)} vs M-1`} />
            
              <MetricCard
              libelle="Agents QR actifs"
              valeur={`${formatNombre(s.agentsActifs)} / ${formatNombre(s.agentsTotal)}`}
              detail="date de référence" />
            
              <MetricCard
              libelle="Appros réseau"
              valeur={formatFcfa(s.montantAppros, true)}
              unite="FCFA" />
            
              <MetricCard
              libelle="Destockages réseau"
              valeur={formatFcfa(s.montantDestockages, true)}
              unite="FCFA" />
            
            </GrilleMetriques>
          }
        </BlocAsync>

        <SectionCash mois={moisCash} />
        <SectionReactivite />
        <SectionQr dateRef={dateQr} />
        <SectionAppro mois={moisAppro} />
      </div>
    </div>);

}