/**
 * src/services/cash.ts
 * =====================
 * Remplace le mock : appelle les endpoints /cash/* de l'API FastAPI.
 */

import { api, qs } from './api';
import type { CashflowPos, TypeOp } from '../types';

// ── Types locaux (mapping API → frontend) ──────────────────────────────────────

export interface LigneCashCommercial {
  commercialId: number;
  dsmName: string;
  cashIn: number;
  cashOut: number;
  nbTransactions: number;
}

export interface LigneAppro {
  commercialId: number;
  dsmName: string;
  nbAppros: number;
  montantAppros: number;
  nbDestockages: number;
  montantDestockages: number;
}

// ── Helpers de mapping ─────────────────────────────────────────────────────────

function mapCashCommercial(r: Record<string, unknown>): LigneCashCommercial {
  return {
    commercialId:   r.commercial_id as number,
    dsmName:        r.dsm_name as string,
    cashIn:         r.cash_in as number,
    cashOut:        r.cash_out as number,
    nbTransactions: r.nb_transactions as number,
  };
}

function mapPos(r: Record<string, unknown>): CashflowPos {
  return {
    posId:       r.pos_id as number,
    acceptorId:  r.acceptor_id as string,
    agentName:   r.agent_name as string,
    agentMsisdn: r.agent_msisdn as string,
    mois:        r.mois as string,
    cashIn:      r.cash_in as number,
    cashOut:     r.cash_out as number,
  };
}

function mapAppro(r: Record<string, unknown>): LigneAppro {
  return {
    commercialId:      r.commercial_id as number,
    dsmName:           r.dsm_name as string,
    nbAppros:          r.nb_appros as number,
    montantAppros:     r.montant_appros as number,
    nbDestockages:     r.nb_destockages as number,
    montantDestockages: r.montant_destockages as number,
  };
}

// ── Cash commercial ────────────────────────────────────────────────────────────

export async function getCashParCommercial(mois: string): Promise<LigneCashCommercial[]> {
  const data = await api.get<Record<string, unknown>[]>(`/cash/commercial${qs({ mois })}`);
  return data.map(mapCashCommercial);
}

export async function getEvolutionCashReseau(): Promise<{ mois: string; cashIn: number; cashOut: number }[]> {
  const data = await api.get<{ mois: string; cash_in: number; cash_out: number }[]>(
    '/cash/commercial/evolution',
  );
  return data.map(r => ({ mois: r.mois, cashIn: r.cash_in, cashOut: r.cash_out }));
}

export async function getMoisCash(): Promise<string[]> {
  const data = await api.get<{ mois: string; cash_in: number; cash_out: number }[]>(
    '/cash/commercial/evolution',
  );
  return data.map(r => r.mois);
}

export async function getAlertesSeuilCommerciaux(mois: string) {
  const data = await api.get<{
    seuil_in: number;
    seuil_out: number;
    lignes: Record<string, unknown>[];
  }>(`/cash/alertes-commercial${qs({ mois })}`);
  return {
    seuilIn:  data.seuil_in,
    seuilOut: data.seuil_out,
    lignes:   data.lignes.map(r => ({
      ...mapCashCommercial(r),
      ecartIn:  r.ecart_in as number,
      ecartOut: r.ecart_out as number,
    })),
  };
}

// ── Cash Flow POS ──────────────────────────────────────────────────────────────

export async function getMoisCashflowPos(): Promise<string[]> {
  return api.get<string[]>('/cash/pos/mois');
}

export async function getCashflowPos(mois: string): Promise<CashflowPos[]> {
  const data = await api.get<Record<string, unknown>[]>(`/cash/pos${qs({ mois })}`);
  return data.map(mapPos);
}

export async function getClassementPos(
  mois: string,
  flux: 'cashIn' | 'cashOut',
  n: number,
) {
  const fluxApi = flux === 'cashIn' ? 'cash_in' : 'cash_out';
  const data = await api.get<{
    top: Record<string, unknown>[];
    flop: Record<string, unknown>[];
    total: number;
  }>(`/cash/pos/classement${qs({ mois, flux: fluxApi, n })}`);
  return {
    top:   data.top.map(mapPos),
    flop:  data.flop.map(mapPos),
    total: data.total,
  };
}

export async function getAlertesSeuilPos(mois: string) {
  const data = await api.get<{
    seuil_in: number;
    seuil_out: number;
    lignes: Record<string, unknown>[];
  }>(`/cash/pos/alertes${qs({ mois })}`);
  return {
    seuilIn:  data.seuil_in,
    seuilOut: data.seuil_out,
    lignes:   data.lignes.map(r => ({
      ...mapPos(r),
      ecartIn:  r.ecart_in as number,
      ecartOut: r.ecart_out as number,
    })),
  };
}

export async function getComparaisonMoMPos(moisListe: string[]) {
  const data = await api.post<{
    mois: string[];
    top_par_mois: Record<string, Record<string, unknown>[]>;
    flop_par_mois: Record<string, Record<string, unknown>[]>;
    top_cumule: { acceptor_id: string; agent_name: string; cumul: number }[];
    constants_top: string[];
    constants_flop: string[];
  }>('/cash/pos/mom', { mois: moisListe });

  const topParMois: Record<string, CashflowPos[]> = {};
  const flopParMois: Record<string, CashflowPos[]> = {};
  for (const m of data.mois) {
    topParMois[m]  = (data.top_par_mois[m]  ?? []).map(mapPos);
    flopParMois[m] = (data.flop_par_mois[m] ?? []).map(mapPos);
  }
  return {
    mois:         data.mois,
    topParMois,
    flopParMois,
    topCumule:    data.top_cumule.map(r => ({
      acceptorId: r.acceptor_id,
      agentName:  r.agent_name,
      cumul:      r.cumul,
    })),
    constantsTop:  data.constants_top,
    constantsFlop: data.constants_flop,
  };
}

// ── Appro / Destockage ─────────────────────────────────────────────────────────

export async function getMoisAppro(): Promise<string[]> {
  return api.get<string[]>('/cash/appro/mois');
}

export async function getApproParCommercial(
  mois: string,
  commercialId?: number,
): Promise<LigneAppro[]> {
  const data = await api.get<Record<string, unknown>[]>(
    `/cash/appro${qs({ mois, commercial_id: commercialId })}`,
  );
  return data.map(mapAppro);
}

export async function getEvolutionAppro(commercialId?: number) {
  const data = await api.get<{
    mois: string;
    montant_appros: number;
    montant_destockages: number;
    nb_appros: number;
    nb_destockages: number;
  }[]>(`/cash/appro/evolution${qs({ commercial_id: commercialId })}`);
  return data.map(r => ({
    mois:               r.mois,
    montantAppros:      r.montant_appros,
    montantDestockages: r.montant_destockages,
    nbAppros:           r.nb_appros,
    nbDestockages:      r.nb_destockages,
  }));
}

export async function getDetailAppro(filtres: {
  commercialId?: number;
  mois?: string;
  typeOp?: TypeOp;
}) {
  const data = await api.get<{
    id: number;
    commercial_id: number;
    dsm_name: string;
    date_op: string;
    type_op: TypeOp;
    nb_ops: number;
    montant: number;
    source_fichier?: string;
  }[]>(`/cash/appro/detail${qs({
    commercial_id: filtres.commercialId,
    mois:          filtres.mois,
    type_op:       filtres.typeOp,
  })}`);
  return data.map(r => ({
    id:            r.id,
    commercialId:  r.commercial_id,
    dsmName:       r.dsm_name,
    dateOp:        r.date_op,
    typeOp:        r.type_op,
    nbOps:         r.nb_ops,
    montant:       r.montant,
    sourceFichier: r.source_fichier,
  }));
}

// ── MoM ────────────────────────────────────────────────────────────────────────

export async function getCashMoM(mois: string, commercialId?: number) {
  const data = await api.get<{
    mois: string;
    precedent: string;
    lignes: {
      commercial_id: number;
      dsm_name: string;
      cash_in_precedent: number;
      cash_in: number;
      cash_out_precedent: number;
      cash_out: number;
    }[];
  }>(`/cash/mom${qs({ mois, commercial_id: commercialId })}`);
  return {
    mois:      data.mois,
    precedent: data.precedent,
    lignes:    data.lignes.map(r => ({
      commercialId:      r.commercial_id,
      dsmName:           r.dsm_name,
      cashInPrecedent:   r.cash_in_precedent,
      cashIn:            r.cash_in,
      cashOutPrecedent:  r.cash_out_precedent,
      cashOut:           r.cash_out,
    })),
  };
}

export async function getApproMoM(mois: string, commercialId?: number) {
  const data = await api.get<{
    mois: string;
    precedent: string;
    lignes: {
      dsm_name: string;
      appro_precedent: number;
      appro: number;
      destoc_precedent: number;
      destockage: number;
    }[];
  }>(`/cash/appro/mom${qs({ mois, commercial_id: commercialId })}`);
  return {
    mois:      data.mois,
    precedent: data.precedent,
    lignes:    data.lignes.map(r => ({
      dsmName:         r.dsm_name,
      apprPrecedent:   r.appro_precedent,
      appro:           r.appro,
      destocPrecedent: r.destoc_precedent,
      destockage:      r.destockage,
    })),
  };
}

// ── Compat : fonctions utilisées par d'autres modules ─────────────────────────

export function cashParCommercialSync(_mois: string): LigneCashCommercial[] {
  // Synchronous compat stub — utilise getCashParCommercial() en async dans les composants
  return [];
}

export function approParCommercialSync(_mois: string): LigneAppro[] {
  return [];
}

export function seuilCourant(_typeFlux: string, _mois: string): number {
  return 0;
}
