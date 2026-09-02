import React from 'react';
import { Section, TitreBloc } from '../ui/Section';
import { BlocAsync, Squelette } from '../ui/States';
import { GrilleMetriques, MetricCard } from '../MetricCard';
import { BarresHorizontales } from '../charts/Charts';
import { useAsync } from '../../hooks/useAsync';
import { getReactivite } from '../../services/terrain';
import { formatNombre } from '../../utils/format';
import { somme } from '../../utils/business';

export function SectionReactivite() {
  const reactivite = useAsync(() => getReactivite(), []);

  return (
    <Section
      id="reactivite"
      titre="Réactivité commerciale"
      description="Rythme quotidien relevé sur les derniers CSV bruts MTN traités.">
      
      <BlocAsync etat={reactivite} squelette={<Squelette lignes={4} hauteur="h-14" />}>
        {(lignes) => {
          const meilleur = [...lignes].sort((a, b) => b.txParJour - a.txParJour)[0];
          const faible = [...lignes].sort((a, b) => a.txParJour - b.txParJour)[0];
          const total = somme(lignes.map((l) => l.nbTransactions));
          const moyenne = lignes.length ?
          somme(lignes.map((l) => l.txParJour)) / lignes.length :
          0;

          return (
            <div className="space-y-5">
              <GrilleMetriques colonnes={4}>
                <MetricCard libelle="Total transactions" valeur={formatNombre(total)} principale />
                <MetricCard libelle="Tx / jour moyen" valeur={formatNombre(moyenne)} />
                <MetricCard
                  libelle="Meilleur rythme"
                  valeur={formatNombre(meilleur?.txParJour ?? 0)}
                  detail={meilleur?.dsmName} />
                
                <MetricCard
                  libelle="Rythme le plus faible"
                  valeur={formatNombre(faible?.txParJour ?? 0)}
                  detail={faible?.dsmName} />
                
              </GrilleMetriques>

              <div>
                <TitreBloc>Transactions par jour et par commercial</TitreBloc>
                <BarresHorizontales
                  donnees={[...lignes].
                  sort((a, b) => b.txParJour - a.txParJour).
                  map((l) => ({ dsmName: l.dsmName, txParJour: l.txParJour }))}
                  cleLabel="dsmName"
                  cleValeur="txParJour"
                  monetaire={false}
                  hauteur={260} />
                
              </div>
            </div>);

        }}
      </BlocAsync>
    </Section>);

}