import React, { useState } from 'react';
import { AlertTriangleIcon } from 'lucide-react';
import { Section, TitreBloc } from '../ui/Section';
import { BlocAsync, Squelette } from '../ui/States';
import { BarresGroupees, BarresHorizontales, CourbeEvolution } from '../charts/Charts';
import { DataTable } from '../DataTable';
import { Champ, Select } from '../ui/Field';
import { useAsync } from '../../hooks/useAsync';
import {
  getAlertesSeuilCommerciaux,
  getCashParCommercial,
  getEvolutionCashReseau } from
'../../services/cash';
import { formatFcfa, labelMois } from '../../utils/format';
import { exporterExcel } from '../../utils/export';

type Vue = 'cash_in' | 'cash_out' | 'comparaison';

export function SectionCash({ mois }: {mois: string;}) {
  const [vue, setVue] = useState<Vue>('cash_in');
  const [topN, setTopN] = useState(5);

  const cash = useAsync(() => getCashParCommercial(mois), [mois]);
  const evolution = useAsync(() => getEvolutionCashReseau(), []);
  const alertes = useAsync(() => getAlertesSeuilCommerciaux(mois), [mois]);

  return (
    <Section
      id="cash"
      titre="Cash In / Cash Out"
      description={`Commissions par commercial sur ${labelMois(mois)}.`}
      actions={
      <>
          <Champ label="Vue" htmlFor="vue-cash" className="w-44">
            <Select
            id="vue-cash"
            className="h-8 text-xs"
            value={vue}
            onChange={(e) => setVue(e.target.value as Vue)}>
            
              <option value="cash_in">Cash In seul</option>
              <option value="cash_out">Cash Out seul</option>
              <option value="comparaison">Comparaison</option>
            </Select>
          </Champ>
          <Champ label="Top / Flop" htmlFor="topn-cash" className="w-28">
            <Select
            id="topn-cash"
            className="h-8 text-xs"
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}>
            
              {[5, 8, 10, 15, 20].map((n) =>
            <option key={n} value={n}>
                  {n}
                </option>
            )}
            </Select>
          </Champ>
        </>
      }>
      
      <BlocAsync etat={cash} squelette={<Squelette lignes={6} hauteur="h-6" />}>
        {(lignes) => {
          const triCashIn = [...lignes].sort((a, b) => b.cashIn - a.cashIn);
          const triCashOut = [...lignes].sort((a, b) => b.cashOut - a.cashOut);
          const donnees = triCashIn.map((l) => ({
            dsmName: l.dsmName,
            cashIn: l.cashIn,
            cashOut: l.cashOut
          }));

          return (
            <div className="space-y-6">
              {vue === 'comparaison' ?
              <BarresGroupees
                donnees={donnees}
                cleLabel="dsmName"
                series={[
                { cle: 'cashIn', nom: 'Cash In', couleur: '#F5A623' },
                { cle: 'cashOut', nom: 'Cash Out', couleur: '#1A1A1A' }]
                } /> :


              <BarresHorizontales
                donnees={vue === 'cash_in' ? donnees : [...donnees].sort((a, b) => b.cashOut - a.cashOut)}
                cleLabel="dsmName"
                cleValeur={vue === 'cash_in' ? 'cashIn' : 'cashOut'}
                couleur={vue === 'cash_in' ? '#F5A623' : '#1A1A1A'}
                hauteur={280} />

              }

              <div className="grid gap-5 lg:grid-cols-2">
                <div>
                  <TitreBloc>Top {topN} cash in</TitreBloc>
                  <DataTable
                    colonnes={[
                    { cle: 'dsmName', entete: 'Commercial' },
                    {
                      cle: 'cashIn',
                      entete: 'Cash In',
                      numerique: true,
                      rendu: (l) => formatFcfa(l.cashIn)
                    }]
                    }
                    lignes={triCashIn.slice(0, topN)}
                    cleLigne={(l) => `top-in-${l.commercialId}`}
                    parPage={topN}
                    compact />
                  
                </div>
                <div>
                  <TitreBloc>Flop {topN} cash in</TitreBloc>
                  <DataTable
                    colonnes={[
                    { cle: 'dsmName', entete: 'Commercial' },
                    {
                      cle: 'cashIn',
                      entete: 'Cash In',
                      numerique: true,
                      rendu: (l) => formatFcfa(l.cashIn)
                    }]
                    }
                    lignes={[...triCashIn].reverse().slice(0, topN)}
                    cleLigne={(l) => `flop-in-${l.commercialId}`}
                    parPage={topN}
                    compact />
                  
                </div>
                <div>
                  <TitreBloc>Top {topN} cash out</TitreBloc>
                  <DataTable
                    colonnes={[
                    { cle: 'dsmName', entete: 'Commercial' },
                    {
                      cle: 'cashOut',
                      entete: 'Cash Out',
                      numerique: true,
                      rendu: (l) => formatFcfa(l.cashOut)
                    }]
                    }
                    lignes={triCashOut.slice(0, topN)}
                    cleLigne={(l) => `top-out-${l.commercialId}`}
                    parPage={topN}
                    compact />
                  
                </div>
                <div>
                  <TitreBloc>Flop {topN} cash out</TitreBloc>
                  <DataTable
                    colonnes={[
                    { cle: 'dsmName', entete: 'Commercial' },
                    {
                      cle: 'cashOut',
                      entete: 'Cash Out',
                      numerique: true,
                      rendu: (l) => formatFcfa(l.cashOut)
                    }]
                    }
                    lignes={[...triCashOut].reverse().slice(0, topN)}
                    cleLigne={(l) => `flop-out-${l.commercialId}`}
                    parPage={topN}
                    compact
                    onExport={() =>
                    exporterExcel(`cash-${mois}`, [
                    {
                      nom: 'Cash par commercial',
                      lignes: lignes.map((l) => ({
                        Commercial: l.dsmName,
                        'Cash In': l.cashIn,
                        'Cash Out': l.cashOut,
                        'Nb transactions': l.nbTransactions
                      }))
                    }]
                    )
                    } />
                  
                </div>
              </div>

              <BlocAsync etat={alertes} squelette={<Squelette lignes={2} />}>
                {(donneesAlertes) =>
                donneesAlertes.lignes.length ?
                <div className="rounded-md border border-[#F3DBA9] bg-albarka-yellow-soft px-4 py-3">
                      <div className="flex items-center gap-2">
                        <AlertTriangleIcon className="h-4 w-4 text-[#8A5A05]" aria-hidden />
                        <p className="text-xs font-semibold text-[#8A5A05]">
                          {donneesAlertes.lignes.length} commercial(aux) sous le seuil configuré
                          (CI {formatFcfa(donneesAlertes.seuilIn)} · CO{' '}
                          {formatFcfa(donneesAlertes.seuilOut)} FCFA)
                        </p>
                      </div>
                      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-2xs text-[#8A5A05]">
                        {donneesAlertes.lignes.map((l) =>
                    <li key={l.commercialId} className="num">
                            {l.dsmName} · écart CI {formatFcfa(l.ecartIn)}
                          </li>
                    )}
                      </ul>
                    </div> :

                <p className="text-xs text-albarka-muted">
                      Aucun commercial sous les seuils configurés ce mois-ci.
                    </p>

                }
              </BlocAsync>

              <div>
                <TitreBloc>Évolution mensuelle du réseau</TitreBloc>
                <BlocAsync etat={evolution} squelette={<Squelette lignes={4} />}>
                  {(series) =>
                  <CourbeEvolution
                    donnees={series.map((s) => ({
                      mois: labelMois(s.mois),
                      cashIn: s.cashIn,
                      cashOut: s.cashOut
                    }))}
                    cleLabel="mois"
                    series={[
                    { cle: 'cashIn', nom: 'Cash In', couleur: '#F5A623' },
                    { cle: 'cashOut', nom: 'Cash Out', couleur: '#1A1A1A' }]
                    } />

                  }
                </BlocAsync>
              </div>
            </div>);

        }}
      </BlocAsync>
    </Section>);

}