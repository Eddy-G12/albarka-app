/**
 * src/services/qr.ts
 * ===================
 * Remplace le mock : appelle les endpoints /qr/* de l'API FastAPI.
 */

import { api, qs } from './api';
import type { QrAgent, QrStatut } from '../types';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface RepartitionQr {
  total: number;
  parStatut: Record<QrStatut, number>;
  tauxDeploiement: number;
  tauxUtilisation: number;
  tauxNonUtilises: number;
  tauxRisque: number;
  tauxSansQr: number;
}

export interface MouvementQr {
  posMsisdn: string;
  posName: string;
  dsmName: string;
  segmentGroup: string;
  statutAvant: QrStatut;
  statutApres: QrStatut;
}

// ── Helpers de mapping ─────────────────────────────────────────────────────────

function mapAgent(r: Record<string, unknown>): QrAgent {
  return {
    posMsisdn:      String(r.pos_msisdn ?? ''),
    posName:        String(r.pos_name ?? ''),
    dsmName:        String(r.dsm_name ?? ''),
    segmentGroup:   String(r.segment_group ?? ''),
    region:         String(r.region ?? ''),
    town:           String(r.town ?? ''),
    statut:         r.statut as QrStatut,
    lastQrCoDate:   (r.last_qr_co_date as string | null) ?? null,
    activeDeployed: (r.active_deployed as number | null) ?? null,
    active30:       (r.active_30 as number) ?? 0,
  };
}

function mapRepartition(r: Record<string, unknown>): RepartitionQr {
  const parStatut = r.par_statut as Record<QrStatut, number>;
  return {
    total:           r.total as number,
    parStatut,
    tauxDeploiement: r.taux_deploiement as number,
    tauxUtilisation: r.taux_utilisation as number,
    tauxNonUtilises: r.taux_non_utilises as number,
    tauxRisque:      r.taux_risque as number,
    tauxSansQr:      r.taux_sans_qr as number,
  };
}

// ── Endpoints ─────────────────────────────────────────────────────────────────

export async function getDatesQr(): Promise<string[]> {
  return api.get<string[]>('/qr/dates');
}

export async function getRepartitionQr(
  dateRef: string,
  dsmName?: string,
  segmentGroup?: string,
): Promise<{ agents: QrAgent[]; repartition: RepartitionQr }> {
  const data = await api.get<{
    agents: Record<string, unknown>[];
    repartition: Record<string, unknown>;
  }>(`/qr/repartition${qs({ date_ref: dateRef, dsm_name: dsmName, segment_group: segmentGroup })}`);
  return {
    agents:      data.agents.map(mapAgent),
    repartition: mapRepartition(data.repartition),
  };
}

export async function getQrParSegment(dateRef: string, dsmName?: string, segmentGroup?: string) {
  const data = await api.get<{
    segment: string;
    total: number;
    actif: number;
    risque: number;
    non_utilise: number;
    sans_qr: number;
  }[]>(`/qr/segments${qs({ date_ref: dateRef, dsm_name: dsmName, segment_group: segmentGroup })}`);
  return data.map(r => ({
    segment:    r.segment,
    total:      r.total,
    actif:      r.actif,
    risque:     r.risque,
    nonUtilise: r.non_utilise,
    sansQr:     r.sans_qr,
  }));
}

export async function getQrParDsm(dateRef: string) {
  const data = await api.get<{
    dsm_name: string;
    total: number;
    actif: number;
    risque: number;
    non_utilise: number;
    sans_qr: number;
    taux_utilisation: number;
  }[]>(`/qr/dsm${qs({ date_ref: dateRef })}`);
  return data.map(r => ({
    dsmName:         r.dsm_name,
    total:           r.total,
    actif:           r.actif,
    risque:          r.risque,
    non_utilise:     r.non_utilise,
    sans_qr:         r.sans_qr,
    tauxUtilisation: r.taux_utilisation,
  }));
}

export async function getAgentsPrioritaires(
  dateRef: string,
  dsmName?: string,
  segmentGroup?: string,
): Promise<QrAgent[]> {
  const data = await api.get<Record<string, unknown>[]>(
    `/qr/prioritaires${qs({ date_ref: dateRef, dsm_name: dsmName, segment_group: segmentGroup })}`,
  );
  return data.map(mapAgent);
}

export async function getAgentsQr(
  dateRef: string,
  dsmName?: string,
  segmentGroup?: string,
  statut?: string,
): Promise<QrAgent[]> {
  const data = await api.get<Record<string, unknown>[]>(
    `/qr/agents${qs({ date_ref: dateRef, dsm_name: dsmName, segment_group: segmentGroup, statut })}`,
  );
  return data.map(mapAgent);
}

export async function getComparaisonQr(dateA: string, dateB: string) {
  const data = await api.get<{
    date_a: string;
    date_b: string;
    repartition_a: Record<string, unknown>;
    repartition_b: Record<string, unknown>;
    par_segment: { segment: string; avant: number; apres: number }[];
    mouvements: {
      pos_msisdn: string;
      pos_name: string;
      dsm_name: string;
      segment_group: string;
      statut_avant: string;
      statut_apres: string;
    }[];
  }>(`/qr/comparaison${qs({ date_a: dateA, date_b: dateB })}`);

  return {
    dateA:         data.date_a,
    dateB:         data.date_b,
    repartitionA:  mapRepartition(data.repartition_a),
    repartitionB:  mapRepartition(data.repartition_b),
    parSegment:    data.par_segment,
    mouvements:    data.mouvements.map(m => ({
      posMsisdn:    m.pos_msisdn,
      posName:      m.pos_name,
      dsmName:      m.dsm_name,
      segmentGroup: m.segment_group,
      statutAvant:  m.statut_avant as QrStatut,
      statutApres:  m.statut_apres as QrStatut,
    })),
  };
}

export async function getQrMoM(dateM1: string, dateM: string, dsmName?: string) {
  return api.get<{
    date_m1: string;
    date_m: string;
    repartition_m1: Record<string, unknown>;
    repartition_m: Record<string, unknown>;
  }>(`/qr/mom${qs({ date_m1: dateM1, date_m: dateM, dsm_name: dsmName })}`);
}

// ── Compat sync (utilisée dans d'anciens imports) ──────────────────────────────
export function agentsQrSync(_dateRef: string, _dsmName?: string): QrAgent[] {
  return [];
}
export function repartitionSync(_agents: QrAgent[]): RepartitionQr {
  return {
    total: 0,
    parStatut: { actif: 0, risque: 0, non_utilise: 0, sans_qr: 0 },
    tauxDeploiement: 0, tauxUtilisation: 0,
    tauxNonUtilises: 0, tauxRisque: 0, tauxSansQr: 0,
  };
}
