import React from 'react';
import { Champ, Select } from './ui/Field';
import { DATES_QR, MOIS_DISPONIBLES } from '../data/seed';
import { labelDate, labelMois } from '../utils/format';

export function SelecteurMois({
  label = 'Mois',
  valeur,
  onChange,
  id,
  mois = MOIS_DISPONIBLES






}: {label?: string;valeur: string;onChange: (mois: string) => void;id?: string;mois?: string[];}) {
  const identifiant = id ?? `mois-${label.replace(/\s/g, '-').toLowerCase()}`;
  return (
    <Champ label={label} htmlFor={identifiant} className="w-44">
      <Select id={identifiant} value={valeur} onChange={(e) => onChange(e.target.value)}>
        {[...mois].reverse().map((m) =>
        <option key={m} value={m}>
            {labelMois(m)}
          </option>
        )}
      </Select>
    </Champ>);

}

export function SelecteurDateQr({
  label = 'Date de référence QR',
  valeur,
  onChange,
  id,
  dates = DATES_QR






}: {label?: string;valeur: string;onChange: (date: string) => void;id?: string;dates?: string[];}) {
  const identifiant = id ?? `dateqr-${label.replace(/\s/g, '-').toLowerCase()}`;
  return (
    <Champ label={label} htmlFor={identifiant} className="w-48">
      <Select id={identifiant} value={valeur} onChange={(e) => onChange(e.target.value)}>
        {[...dates].reverse().map((d) =>
        <option key={d} value={d}>
            {labelDate(d)}
          </option>
        )}
      </Select>
    </Champ>);

}

export function SelecteurCommercial({
  label = 'Commercial',
  valeur,
  onChange,
  commerciaux,
  toutLibelle = 'Tous les commerciaux',
  id = 'commercial'







}: {label?: string;valeur: number | 'tous';onChange: (valeur: number | 'tous') => void;commerciaux: {id: number;dsmName: string;}[];toutLibelle?: string;id?: string;}) {
  return (
    <Champ label={label} htmlFor={id} className="w-52">
      <Select
        id={id}
        value={String(valeur)}
        onChange={(e) => onChange(e.target.value === 'tous' ? 'tous' : Number(e.target.value))}>
        
        <option value="tous">{toutLibelle}</option>
        {commerciaux.map((c) =>
        <option key={c.id} value={c.id}>
            {c.dsmName}
          </option>
        )}
      </Select>
    </Champ>);

}