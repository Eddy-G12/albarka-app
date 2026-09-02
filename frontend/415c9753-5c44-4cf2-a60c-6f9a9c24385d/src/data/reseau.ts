import type { CashflowPos, Pos, QrAgent, QrStatut } from '../types';
import { classerAgentQr } from '../utils/business';
import { COMMERCIAUX } from './referentiel';
import { DATES_QR, MOIS_DISPONIBLES, choisir, creerRng, entreBornes } from './seed';

const PRENOMS = [
'NGONO',
'MBALLA',
'FOUDA',
'TCHINDA',
'EBODE',
'NJOYA',
'ATANGANA',
'KAMDEM',
'MOUKOKO',
'BIYA',
'SANDA',
'OUMAROU',
'DJOMO',
'ESSOMBA',
'MANGA',
'NKOLO',
'TAMBA',
'WOUAMBA'];


const SUFFIXES = [
'SERVICES',
'BUSINESS',
'MULTISERVICES',
'SHOP',
'ETS',
'TRADING',
'POINT MOMO',
'AGENCE'];


const SEGMENTS = [
'Retail Standard',
'Retail Premium',
'Marchand',
'Kiosque',
'Station service'];


const REGIONS: {region: string;villes: string[];}[] = [
{ region: 'Littoral', villes: ['Douala', 'Nkongsamba', 'Edéa'] },
{ region: 'Centre', villes: ['Yaoundé', 'Mbalmayo', 'Obala'] },
{ region: 'Ouest', villes: ['Bafoussam', 'Dschang', 'Mbouda'] },
{ region: 'Sud-Ouest', villes: ['Buéa', 'Limbé', 'Kumba'] },
{ region: 'Nord', villes: ['Garoua', 'Guider'] },
{ region: 'Est', villes: ['Bertoua', 'Batouri'] },
{ region: 'Adamaoua', villes: ['Ngaoundéré', 'Meiganga'] }];


const NB_POS = 731;

function nomAgent(rng: () => number): string {
  return `${choisir(rng, PRENOMS)} ${choisir(rng, SUFFIXES)}`;
}

function construirePos(): Pos[] {
  const rng = creerRng(20260801);
  return Array.from({ length: NB_POS }, (_, i) => ({
    id: i + 1,
    acceptorId: `POS${String(100_000 + i * 7).padStart(6, '0')}`,
    agentMsisdn: `2376${entreBornes(rng, 50, 99)}${String(entreBornes(rng, 100000, 999999))}`,
    agentName: nomAgent(rng)
  }));
}

export const POS_LIST: Pos[] = construirePos();

function construireCashflow(): CashflowPos[] {
  const rng = creerRng(77321);
  const lignes: CashflowPos[] = [];
  POS_LIST.forEach((pos) => {
    // profil de performance stable par POS, avec dérive mensuelle
    const base = entreBornes(rng, 8_000, 190_000);
    const ratioOut = 0.45 + rng() * 0.5;
    MOIS_DISPONIBLES.forEach((mois, index) => {
      const derive = 0.82 + rng() * 0.4 + index * 0.03;
      const cashIn = Math.round(base * derive);
      lignes.push({
        posId: pos.id,
        acceptorId: pos.acceptorId,
        agentName: pos.agentName,
        agentMsisdn: pos.agentMsisdn,
        mois,
        cashIn,
        cashOut: Math.round(cashIn * ratioOut)
      });
    });
  });
  return lignes;
}

export const CASHFLOW_POS: CashflowPos[] = construireCashflow();

function construireQr(): Record<string, QrAgent[]> {
  const resultat: Record<string, QrAgent[]> = {};
  DATES_QR.forEach((dateRef, indexDate) => {
    const rng = creerRng(4200 + indexDate * 131);
    resultat[dateRef] = POS_LIST.map((pos, i) => {
      const zone = REGIONS[i % REGIONS.length];
      const tirage = rng();
      // la couverture s'améliore légèrement de date en date
      const deploye = tirage > 0.11 - indexDate * 0.02 ? 1 : null;
      const active30 = deploye && rng() > 0.14 - indexDate * 0.015 ? 1 : 0;
      const jours = entreBornes(rng, 0, 46);
      const last = new Date(Date.parse(`${dateRef}T00:00:00Z`) - jours * 86_400_000).
      toISOString().
      slice(0, 10);
      const statut: QrStatut = classerAgentQr({
        activeDeployed: deploye,
        active30,
        lastQrCoDate: deploye ? last : null,
        dateRef
      });
      return {
        posMsisdn: pos.agentMsisdn,
        posName: pos.agentName,
        dsmName: COMMERCIAUX[i % COMMERCIAUX.length].dsmName,
        segmentGroup: SEGMENTS[i % SEGMENTS.length],
        region: zone.region,
        town: zone.villes[i % zone.villes.length],
        statut,
        lastQrCoDate: deploye ? last : null,
        activeDeployed: deploye,
        active30
      };
    });
  });
  return resultat;
}

export const QR_PAR_DATE: Record<string, QrAgent[]> = construireQr();