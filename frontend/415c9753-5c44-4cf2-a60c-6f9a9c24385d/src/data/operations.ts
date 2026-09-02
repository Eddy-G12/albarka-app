import type {
  ApproEntry,
  ClientServi,
  PointTouche,
  ReactiviteIndicateur,
  TransactionMomo } from
'../types';
import { COMMERCIAUX } from './referentiel';
import {
  MOIS_DISPONIBLES,
  choisir,
  creerRng,
  entreBornes,
  estWeekend,
  joursDuMois } from
'./seed';

const NOMS_CLIENTS = [
'BOUTIQUE LA GRACE',
'ETS SANTA MARIA',
'CALL BOX AKWA',
'MAMA NGO PROVISION',
'POINT MOMO CARREFOUR',
'ALIMENTATION BONNE FOI',
'KIOSQUE ESSOS',
'TANTINE JEANNE',
'CYBER NDOKOTI',
'STATION TOTAL BEPANDA',
'ETS FRERES UNIS',
'SUPERETTE MOKOLO',
'PHARMACIE DU LAC',
'QUINCAILLERIE SAWA',
'AGENCE VOYAGE BUEA'];


/** Cash in / cash out consolidé par commercial et par mois. */
function construireTransactions(): TransactionMomo[] {
  const rng = creerRng(9012);
  const lignes: TransactionMomo[] = [];
  COMMERCIAUX.forEach((commercial, index) => {
    const socle = 38_000 + index * 9_400 + entreBornes(rng, 0, 22_000);
    MOIS_DISPONIBLES.forEach((mois, i) => {
      const derive = 0.85 + rng() * 0.35 + i * 0.04;
      const cashIn = Math.round(socle * derive * (commercial.actif ? 1 : 0.35));
      lignes.push({
        commercialId: commercial.id,
        mois,
        cashIn,
        cashOut: Math.round(cashIn * (0.52 + rng() * 0.4)),
        nbTransactions: entreBornes(rng, 380, 1_640)
      });
    });
  });
  return lignes;
}

export const TRANSACTIONS_MOMO: TransactionMomo[] = construireTransactions();

/** Appro / destockage journaliers — uniquement les commerciaux avec alias. */
function construireAppro(): ApproEntry[] {
  const rng = creerRng(5511);
  const lignes: ApproEntry[] = [];
  let id = 1;
  COMMERCIAUX.filter((c) => c.alias).forEach((commercial) => {
    MOIS_DISPONIBLES.forEach((mois) => {
      joursDuMois(mois).forEach((date) => {
        if (estWeekend(date) || rng() > 0.78) return;
        lignes.push({
          id: id++,
          commercialId: commercial.id,
          dateOp: date,
          typeOp: 'appro',
          nbOps: entreBornes(rng, 1, 7),
          montant: entreBornes(rng, 250_000, 4_200_000),
          sourceFichier: `${commercial.dsmName}-${mois}.csv`
        });
        if (rng() > 0.42) {
          lignes.push({
            id: id++,
            commercialId: commercial.id,
            dateOp: date,
            typeOp: 'destockage',
            nbOps: entreBornes(rng, 1, 5),
            montant: entreBornes(rng, 180_000, 2_900_000),
            sourceFichier: `${commercial.dsmName}-${mois}.csv`
          });
        }
      });
    });
  });
  return lignes;
}

export const APPRO: ApproEntry[] = construireAppro();

function construirePointsTouches(): PointTouche[] {
  const rng = creerRng(3307);
  const lignes: PointTouche[] = [];
  COMMERCIAUX.forEach((commercial) => {
    MOIS_DISPONIBLES.forEach((mois) => {
      joursDuMois(mois).forEach((date) => {
        if (estWeekend(date) || rng() > 0.84) return;
        lignes.push({
          commercialId: commercial.id,
          dateOp: date,
          nbPoints: entreBornes(rng, 4, 48)
        });
      });
    });
  });
  return lignes;
}

export const POINTS_TOUCHES: PointTouche[] = construirePointsTouches();

function construireClientsServis(): ClientServi[] {
  const rng = creerRng(6620);
  const lignes: ClientServi[] = [];
  COMMERCIAUX.filter((c) => c.alias).forEach((commercial) => {
    MOIS_DISPONIBLES.forEach((mois) => {
      joursDuMois(mois).forEach((date) => {
        if (rng() > 0.35) return;
        const nbClients = entreBornes(rng, 2, 6);
        for (let i = 0; i < nbClients; i += 1) {
          lignes.push({
            commercialId: commercial.id,
            dateOp: date,
            nomContrepartie: choisir(rng, NOMS_CLIENTS),
            msisdn: `2376${entreBornes(rng, 50, 99)}${entreBornes(rng, 100000, 999999)}`,
            nbTransactions: entreBornes(rng, 1, 5)
          });
        }
      });
    });
  });
  return lignes;
}

export const CLIENTS_SERVIS: ClientServi[] = construireClientsServis();

function construireReactivite(): ReactiviteIndicateur[] {
  const rng = creerRng(1188);
  return COMMERCIAUX.filter((c) => c.actif).map((commercial) => {
    const joursActifs = entreBornes(rng, 12, 24);
    const nbTransactions = joursActifs * entreBornes(rng, 14, 62);
    const donneesCompletes = commercial.alias !== null;
    return {
      commercialId: commercial.id,
      dsmName: commercial.dsmName,
      nbTransactions,
      joursActifs,
      txParJour: Number((nbTransactions / joursActifs).toFixed(1)),
      clientsParJour: Number((entreBornes(rng, 60, 220) / 10).toFixed(1)),
      tempsMortMedian: donneesCompletes ? entreBornes(rng, 12, 78) : null,
      tempsMortMax: donneesCompletes ? entreBornes(rng, 160, 520) : null,
      tempsRechargeMedian: donneesCompletes ? entreBornes(rng, 18, 145) : null,
      tempsRechargeMin: donneesCompletes ? entreBornes(rng, 4, 22) : null
    };
  });
}

export const REACTIVITE: ReactiviteIndicateur[] = construireReactivite();