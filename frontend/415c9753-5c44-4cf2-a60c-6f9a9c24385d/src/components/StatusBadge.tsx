import React from 'react';
import type { QrStatut } from '../types';
import { LIBELLE_STATUT } from '../utils/business';

const CLASSES: Record<QrStatut, string> = {
  actif: 'bg-[#E8F6EF] text-[#14724A] border-[#BFE6D4]',
  risque: 'bg-albarka-yellow-soft text-[#8A5A05] border-[#F3DBA9]',
  non_utilise: 'bg-[#FDEEE4] text-[#9C4715] border-[#F5CDB2]',
  sans_qr: 'bg-[#FDF0EF] text-[#9C2A22] border-[#F2C6C2]'
};

export function StatusBadge({ statut }: {statut: QrStatut;}) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-2xs font-medium ${CLASSES[statut]}`}>
      
      {LIBELLE_STATUT[statut]}
    </span>);

}

export function BadgeNeutre({
  children,
  ton = 'neutre'



}: {children: React.ReactNode;ton?: 'neutre' | 'accent' | 'succes' | 'alerte';}) {
  const classes = {
    neutre: 'bg-albarka-bg text-albarka-muted border-albarka-border',
    accent: 'bg-albarka-yellow-soft text-[#8A5A05] border-[#F3DBA9]',
    succes: 'bg-[#E8F6EF] text-[#14724A] border-[#BFE6D4]',
    alerte: 'bg-[#FDF0EF] text-[#9C2A22] border-[#F2C6C2]'
  }[ton];
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-2xs font-medium ${classes}`}>
      
      {children}
    </span>);

}