import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis } from
'recharts';
import { formatFcfa, formatNombre } from '../../utils/format';

export const COULEURS_SERIES = ['#F5A623', '#1A1A1A', '#6B7280', '#1E9E62', '#E8702A'];

const AXE = { stroke: '#6B7280', fontSize: 11 };

const tooltipStyle = {
  contentStyle: {
    borderRadius: 6,
    border: '1px solid #E9ECEF',
    fontSize: 12,
    boxShadow: '0 8px 24px rgba(26,26,26,0.12)'
  },
  labelStyle: { color: '#1A1A1A', fontWeight: 600 }
};

function formateur(valeur: number, monetaire: boolean) {
  return monetaire ? `${formatFcfa(valeur)} FCFA` : formatNombre(valeur);
}

export function BarresHorizontales({
  donnees,
  cleLabel,
  cleValeur,
  hauteur = 320,
  monetaire = true,
  couleur = COULEURS_SERIES[0],
  surligne








}: {donnees: Record<string, string | number>[];cleLabel: string;cleValeur: string;hauteur?: number;monetaire?: boolean;couleur?: string;surligne?: string;}) {
  return (
    <ResponsiveContainer width="100%" height={hauteur}>
      <BarChart data={donnees} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke="#E9ECEF" />
        <XAxis
          type="number"
          tick={AXE}
          tickFormatter={(v: number) => formatFcfa(v, true)}
          axisLine={false}
          tickLine={false} />
        
        <YAxis
          type="category"
          dataKey={cleLabel}
          tick={AXE}
          width={130}
          axisLine={false}
          tickLine={false} />
        
        <Tooltip
          {...tooltipStyle}
          formatter={(v: number) => formateur(v, monetaire)}
          cursor={{ fill: '#F8F9FA' }} />
        
        <Bar dataKey={cleValeur} radius={[0, 3, 3, 0]} maxBarSize={18}>
          {donnees.map((ligne, index) =>
          <Cell
            key={index}
            fill={surligne && ligne[cleLabel] === surligne ? '#1A1A1A' : couleur} />

          )}
        </Bar>
      </BarChart>
    </ResponsiveContainer>);

}

export function BarresGroupees({
  donnees,
  cleLabel,
  series,
  hauteur = 300,
  monetaire = true






}: {donnees: Record<string, string | number>[];cleLabel: string;series: {cle: string;nom: string;couleur?: string;}[];hauteur?: number;monetaire?: boolean;}) {
  return (
    <ResponsiveContainer width="100%" height={hauteur}>
      <BarChart data={donnees} margin={{ left: 8, right: 8, top: 4, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke="#E9ECEF" />
        <XAxis dataKey={cleLabel} tick={AXE} axisLine={false} tickLine={false} />
        <YAxis
          tick={AXE}
          tickFormatter={(v: number) => formatFcfa(v, true)}
          axisLine={false}
          tickLine={false} />
        
        <Tooltip
          {...tooltipStyle}
          formatter={(v: number) => formateur(v, monetaire)}
          cursor={{ fill: '#F8F9FA' }} />
        
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((serie, index) =>
        <Bar
          key={serie.cle}
          dataKey={serie.cle}
          name={serie.nom}
          fill={serie.couleur ?? COULEURS_SERIES[index % COULEURS_SERIES.length]}
          radius={[3, 3, 0, 0]}
          maxBarSize={26} />

        )}
      </BarChart>
    </ResponsiveContainer>);

}

export function BarresEmpilees({
  donnees,
  cleLabel,
  series,
  hauteur = 300





}: {donnees: Record<string, string | number>[];cleLabel: string;series: {cle: string;nom: string;couleur: string;}[];hauteur?: number;}) {
  return (
    <ResponsiveContainer width="100%" height={hauteur}>
      <BarChart data={donnees} margin={{ left: 8, right: 8, top: 4, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke="#E9ECEF" />
        <XAxis dataKey={cleLabel} tick={AXE} axisLine={false} tickLine={false} />
        <YAxis tick={AXE} axisLine={false} tickLine={false} />
        <Tooltip {...tooltipStyle} cursor={{ fill: '#F8F9FA' }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((serie) =>
        <Bar
          key={serie.cle}
          dataKey={serie.cle}
          name={serie.nom}
          stackId="statut"
          fill={serie.couleur}
          maxBarSize={40} />

        )}
      </BarChart>
    </ResponsiveContainer>);

}

export function CourbeEvolution({
  donnees,
  cleLabel,
  series,
  hauteur = 260,
  monetaire = true






}: {donnees: Record<string, string | number>[];cleLabel: string;series: {cle: string;nom: string;couleur?: string;}[];hauteur?: number;monetaire?: boolean;}) {
  return (
    <ResponsiveContainer width="100%" height={hauteur}>
      <LineChart data={donnees} margin={{ left: 8, right: 12, top: 8, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke="#E9ECEF" />
        <XAxis dataKey={cleLabel} tick={AXE} axisLine={false} tickLine={false} />
        <YAxis
          tick={AXE}
          tickFormatter={(v: number) => formatFcfa(v, true)}
          axisLine={false}
          tickLine={false} />
        
        <Tooltip {...tooltipStyle} formatter={(v: number) => formateur(v, monetaire)} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((serie, index) =>
        <Line
          key={serie.cle}
          type="monotone"
          dataKey={serie.cle}
          name={serie.nom}
          stroke={serie.couleur ?? COULEURS_SERIES[index % COULEURS_SERIES.length]}
          strokeWidth={2}
          dot={{ r: 3 }}
          activeDot={{ r: 5 }} />

        )}
      </LineChart>
    </ResponsiveContainer>);

}