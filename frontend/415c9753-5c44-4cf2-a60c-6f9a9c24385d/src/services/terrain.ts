/**
 * src/services/terrain.ts
 * ========================
 * Remplace le mock : appelle les endpoints /terrain/* de l'API FastAPI.
 */

import { api, qs } from './api';
import type { ReactiviteIndicateur } from '../types';

// ── Types locaux ──────────────────────────────────────────────────────────────

export interface LigneCouverture {
  msisdn: string;
  nom: string;
  profilPos: string | null;
  nbContacts: number;
  premiere: string | null;
  derniere: string | null;
}

// ── Points touchés ─────────────────────────────────────────────────────────────

export async function getSynthesePointsTouches(commercialId?: number) {
  const data = await api.get<{
    par_commercial: {
      commercial_id: number;
      dsm_name: string;
      total_points: number;
      jours_actifs: number;
      moyenne_jour: number;
    }[];
    detail: {
      commercial_id: number;
      dsm_name: string;
      date_op: string;
      nb_points: number;
    }[];
  }>(`/terrain/points-touches${qs({ commercial_id: commercialId })}`);

  return {
    parCommercial: data.par_commercial.map(r => ({
      commercialId: r.commercial_id,
      dsmName:      r.dsm_name,
      totalPoints:  r.total_points,
      joursActifs:  r.jours_actifs,
      moyenneJour:  r.moyenne_jour,
    })),
    detail: data.detail.map(r => ({
      commercialId: r.commercial_id,
      dsmName:      r.dsm_name,
      dateOp:       r.date_op,
      nbPoints:     r.nb_points,
    })),
  };
}

// ── Clients servis ─────────────────────────────────────────────────────────────

export async function getClientsServis(filtres: {
  commercialId?: number;
  du?: string;
  au?: string;
}) {
  const data = await api.get<{
    lignes: {
      msisdn: string;
      nom: string | null;
      nb_transactions: number;
      premiere: string;
      derniere: string;
    }[];
    clients_distincts: number;
    total_transactions: number;
  }>(`/terrain/clients-servis${qs({
    commercial_id: filtres.commercialId,
    du: filtres.du,
    au: filtres.au,
  })}`);

  return {
    lignes: data.lignes.map(r => ({
      msisdn:         r.msisdn,
      nom:            r.nom,
      nbTransactions: r.nb_transactions,
      premiere:       r.premiere,
      derniere:       r.derniere,
    })),
    clientsDistincts:   data.clients_distincts,
    totalTransactions:  data.total_transactions,
  };
}

// ── Réactivité ─────────────────────────────────────────────────────────────────

/** Indicateurs agrégés (depuis clients_servis en base). */
export async function getReactivite(): Promise<ReactiviteIndicateur[]> {
  const data = await api.get<{
    commercial_id: number;
    dsm_name: string;
    alias: string | null;
    nb_transactions: number;
    jours_actifs: number;
    tx_par_jour: number;
    clients_par_jour: number;
    temps_mort_median: number | null;
    temps_mort_max: number | null;
    temps_recharge_median: number | null;
    temps_recharge_min: number | null;
  }[]>('/terrain/reactivite');

  return data.map(r => ({
    commercialId:        r.commercial_id,
    dsmName:             r.dsm_name,
    nbTransactions:      r.nb_transactions,
    joursActifs:         r.jours_actifs,
    txParJour:           r.tx_par_jour,
    clientsParJour:      r.clients_par_jour,
    tempsMortMedian:     r.temps_mort_median,
    tempsMortMax:        r.temps_mort_max,
    tempsRechargeMedian: r.temps_recharge_median,
    tempsRechargeMin:    r.temps_recharge_min,
  }));
}

/** Calcul complet depuis des CSV bruts uploadés. */
export async function calculerReactivite(
  fichiers: File[],
): Promise<ReactiviteIndicateur[]> {
  const form = new FormData();
  for (const f of fichiers) {
    form.append('fichiers', f);
  }
  const data = await api.upload<{
    commercial_id: number;
    dsm_name: string;
    alias: string | null;
    nb_transactions: number;
    jours_actifs: number;
    tx_par_jour: number;
    clients_par_jour: number;
    temps_mort_median: number | null;
    temps_mort_max: number | null;
    temps_recharge_median: number | null;
    temps_recharge_min: number | null;
  }[]>('/terrain/reactivite/calcul', form);

  return data.map(r => ({
    commercialId:        r.commercial_id,
    dsmName:             r.dsm_name,
    nbTransactions:      r.nb_transactions,
    joursActifs:         r.jours_actifs,
    txParJour:           r.tx_par_jour,
    clientsParJour:      r.clients_par_jour,
    tempsMortMedian:     r.temps_mort_median,
    tempsMortMax:        r.temps_mort_max,
    tempsRechargeMedian: r.temps_recharge_median,
    tempsRechargeMin:    r.temps_recharge_min,
  }));
}

// ── Portefeuilles ──────────────────────────────────────────────────────────────

export async function getPortefeuilles(commercialId?: number) {
  const data = await api.get<{
    id: number;
    commercial_id: number;
    dsm_name: string;
    nom: string;
    date_import: string;
    nb_clients: number;
  }[]>(`/terrain/portefeuilles${qs({ commercial_id: commercialId })}`);

  return data.map(r => ({
    id:           r.id,
    commercialId: r.commercial_id,
    dsmName:      r.dsm_name,
    nom:          r.nom,
    dateImport:   r.date_import,
    nbClients:    r.nb_clients,
  }));
}

export async function getClientsPortefeuille(portefeuilleId: number) {
  const data = await api.get<{
    id: number;
    portefeuille_id: number;
    nom: string;
    telephone: string | null;
    localite: string | null;
  }[]>(`/terrain/portefeuilles/${portefeuilleId}/clients`);

  return data.map(r => ({
    id:             r.id,
    portefeuilleId: r.portefeuille_id,
    nom:            r.nom,
    telephone:      r.telephone,
    localite:       r.localite,
  }));
}

/** Couverture depuis CSV bruts uploadés. */
export async function getCouverturePortefeuille(
  portefeuilleId: number,
  fichiers: File[],
) {
  const form = new FormData();
  for (const f of fichiers) {
    form.append('fichiers', f);
  }
  const data = await api.upload<{
    lignes: {
      msisdn: string;
      nom: string;
      profil_pos: string | null;
      nb_contacts: number;
      premiere: string | null;
      derniere: string | null;
    }[];
    clients_touches: number;
    clients_non_touches: number;
    taux_couverture: number;
    total_contacts: number;
  }>(`/terrain/portefeuilles/${portefeuilleId}/couverture`, form);

  return {
    lignes: data.lignes.map(r => ({
      msisdn:     r.msisdn,
      nom:        r.nom,
      profilPos:  r.profil_pos,
      nbContacts: r.nb_contacts,
      premiere:   r.premiere,
      derniere:   r.derniere,
    } as LigneCouverture)),
    clientsTouches:    data.clients_touches,
    clientsNonTouches: data.clients_non_touches,
    tauxCouverture:    data.taux_couverture,
    totalContacts:     data.total_contacts,
  };
}
