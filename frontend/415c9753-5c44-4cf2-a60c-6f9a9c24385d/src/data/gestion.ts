import type {
  ClientPortefeuille,
  ImportRecord,
  Parrainage,
  Portefeuille,
  SuiviPersonne } from
'../types';
import { COMMERCIAUX } from './referentiel';
import { choisir, creerRng, entreBornes, joursDuMois } from './seed';

const PROFILS_POS = [
'MTNC Merchant Account Profile',
'MTNC Retailer Profile',
'MTNC Sub Agent Profile'];


const NOMS = [
'ETS LA CONFIANCE',
'BOUTIQUE SAINT MICHEL',
'CALL BOX DEIDO',
'ALIMENTATION LE BON PRIX',
'MAMA CLARISSE',
'POINT MOMO NEW BELL',
'CYBER LA REFERENCE',
'QUINCAILLERIE BONAMOUSSADI',
'PRESSING NKOLBISSON',
'SUPERETTE BIYEM ASSI'];


export const PORTEFEUILLES: Portefeuille[] = [
{ id: 1, commercialId: 5, nom: 'Portefeuille EWANE Q3', dateImport: '2026-07-04', nbClients: 148 },
{ id: 2, commercialId: 1, nom: 'Portefeuille PARFAIT Douala', dateImport: '2026-07-18', nbClients: 212 },
{ id: 3, commercialId: 3, nom: 'Portefeuille ANTOINE Bonabéri', dateImport: '2026-08-01', nbClients: 96 },
{ id: 4, commercialId: 2, nom: 'Portefeuille STEPHANE Centre', dateImport: '2026-08-12', nbClients: 174 }];


function construireClients(): ClientPortefeuille[] {
  const rng = creerRng(8899);
  const lignes: ClientPortefeuille[] = [];
  let id = 1;
  PORTEFEUILLES.forEach((pf) => {
    for (let i = 0; i < pf.nbClients; i += 1) {
      lignes.push({
        id: id++,
        portefeuilleId: pf.id,
        nom: `${choisir(rng, NOMS)} ${entreBornes(rng, 1, 99)}`,
        telephone: `2376${entreBornes(rng, 50, 99)}${entreBornes(rng, 100000, 999999)}`,
        localite: choisir(rng, PROFILS_POS)
      });
    }
  });
  return lignes;
}

export const CLIENTS_PORTEFEUILLE: ClientPortefeuille[] = construireClients();

export const PERSONNES_PARRAINAGE = [
'Antoine',
'Parfait',
'Erve',
'Ewane',
'Stéphane',
'Theo',
'Nathan'];


function construireParrainages(): Parrainage[] {
  const rng = creerRng(4141);
  const lignes: Parrainage[] = [];
  ['2026-07', '2026-08'].forEach((mois) => {
    joursDuMois(mois).forEach((date) => {
      PERSONNES_PARRAINAGE.forEach((personne) => {
        if (rng() > 0.55) return;
        lignes.push({ personne, dateOp: date, nb: entreBornes(rng, 1, 9) });
      });
    });
  });
  return lignes;
}

export const PARRAINAGES: Parrainage[] = construireParrainages();

export const COMMERCIAUX_SUIVIS = ['CESAIRE', 'ANTOINE', 'PARFAIT', 'ERVE', 'STEPHANE'];

const PERSONNES_SUIVIES = [
'Mme Ngo Bell',
'M. Tchoumi Junior',
'Boutique Espoir',
'M. Sanda Ali',
'Mme Awono',
'Cyber Etoile'];


function construireSuivi(): SuiviPersonne[] {
  const rng = creerRng(2727);
  const lignes: SuiviPersonne[] = [];
  let id = 1;
  const ids = COMMERCIAUX.filter((c) => COMMERCIAUX_SUIVIS.includes(c.dsmName)).map((c) => c.id);
  ['2026-07', '2026-08'].forEach((mois) => {
    joursDuMois(mois).forEach((date) => {
      ids.forEach((commercialId) => {
        if (rng() > 0.22) return;
        lignes.push({
          id: id++,
          commercialId,
          nomPersonne: choisir(rng, PERSONNES_SUIVIES),
          montant: entreBornes(rng, 15_000, 850_000),
          dateHeure: `${date} ${String(entreBornes(rng, 7, 19)).padStart(2, '0')}:${String(
            entreBornes(rng, 0, 59)
          ).padStart(2, '0')}:00`
        });
      });
    });
  });
  return lignes;
}

export const SUIVI_PERSONNES: SuiviPersonne[] = construireSuivi();

export const IMPORTS: ImportRecord[] = [
{
  id: 21,
  typeFichier: 'qr_code',
  cle: 'qr_2026-08-28',
  dateDonnees: '2026-08-28',
  cheminFichier: 'data/qr_code/rapport_2026-08-28.xlsx',
  nbLignes: 731,
  dateExecution: '2026-08-29 08:42:11',
  fichierDisponible: true
},
{
  id: 20,
  typeFichier: 'transactions',
  cle: 'tx_PARFAIT_2026-08',
  dateDonnees: '2026-08',
  cheminFichier: 'data/transactions/PARFAIT_2026-08.xlsx',
  nbLignes: 4_812,
  dateExecution: '2026-08-28 17:05:44',
  fichierDisponible: true
},
{
  id: 19,
  typeFichier: 'transactions',
  cle: 'tx_ANTOINE_2026-08',
  dateDonnees: '2026-08',
  cheminFichier: 'data/transactions/ANTOINE_2026-08.xlsx',
  nbLignes: 3_144,
  dateExecution: '2026-08-28 17:04:02',
  fichierDisponible: true
},
{
  id: 18,
  typeFichier: 'comparatif',
  cle: 'cmp_2026-07-31_2026-08-28',
  dateDonnees: '2026-08-28',
  cheminFichier: 'data/comparatifs/cmp_2026-07-31_2026-08-28.xlsx',
  nbLignes: 731,
  dateExecution: '2026-08-29 09:15:20',
  fichierDisponible: true
},
{
  id: 17,
  typeFichier: 'qr_code',
  cle: 'qr_2026-07-31',
  dateDonnees: '2026-07-31',
  cheminFichier: 'data/qr_code/rapport_2026-07-31.xlsx',
  nbLignes: 731,
  dateExecution: '2026-08-01 07:58:03',
  fichierDisponible: true
},
{
  id: 16,
  typeFichier: 'transactions',
  cle: 'tx_EWANE_2026-07',
  dateDonnees: '2026-07',
  cheminFichier: 'data/transactions/EWANE_2026-07.xlsx',
  nbLignes: 2_760,
  dateExecution: '2026-07-31 16:22:47',
  fichierDisponible: true
},
{
  id: 15,
  typeFichier: 'transactions',
  cle: 'tx_STEPHANE_2026-07',
  dateDonnees: '2026-07',
  cheminFichier: 'data/transactions/STEPHANE_2026-07.xlsx',
  nbLignes: 3_902,
  dateExecution: '2026-07-31 16:20:11',
  fichierDisponible: false
},
{
  id: 14,
  typeFichier: 'comparatif',
  cle: 'cmp_2026-06-30_2026-07-31',
  dateDonnees: '2026-07-31',
  cheminFichier: 'data/comparatifs/cmp_2026-06-30_2026-07-31.xlsx',
  nbLignes: 731,
  dateExecution: '2026-08-01 09:02:35',
  fichierDisponible: true
},
{
  id: 13,
  typeFichier: 'qr_code',
  cle: 'qr_2026-06-30',
  dateDonnees: '2026-06-30',
  cheminFichier: 'data/qr_code/rapport_2026-06-30.xlsx',
  nbLignes: 728,
  dateExecution: '2026-07-01 08:11:59',
  fichierDisponible: true
},
{
  id: 12,
  typeFichier: 'transactions',
  cle: 'tx_ERVE_2026-06',
  dateDonnees: '2026-06',
  cheminFichier: 'data/transactions/ERVE_2026-06.xlsx',
  nbLignes: 2_218,
  dateExecution: '2026-06-30 18:44:10',
  fichierDisponible: false
},
{
  id: 11,
  typeFichier: 'transactions',
  cle: 'tx_PARFAIT_2026-06',
  dateDonnees: '2026-06',
  cheminFichier: 'data/transactions/PARFAIT_2026-06.xlsx',
  nbLignes: 4_405,
  dateExecution: '2026-06-30 18:40:22',
  fichierDisponible: true
},
{
  id: 10,
  typeFichier: 'qr_code',
  cle: 'qr_2026-05-31',
  dateDonnees: '2026-05-31',
  cheminFichier: 'data/qr_code/rapport_2026-05-31.xlsx',
  nbLignes: 722,
  dateExecution: '2026-06-01 08:05:41',
  fichierDisponible: true
},
{
  id: 9,
  typeFichier: 'transactions',
  cle: 'tx_EWANE_2026-05',
  dateDonnees: '2026-05',
  cheminFichier: 'data/transactions/EWANE_2026-05.xlsx',
  nbLignes: 2_531,
  dateExecution: '2026-05-31 17:12:08',
  fichierDisponible: true
},
{
  id: 8,
  typeFichier: 'comparatif',
  cle: 'cmp_2026-05-31_2026-06-30',
  dateDonnees: '2026-06-30',
  cheminFichier: 'data/comparatifs/cmp_2026-05-31_2026-06-30.xlsx',
  nbLignes: 728,
  dateExecution: '2026-07-01 09:31:12',
  fichierDisponible: true
},
{
  id: 7,
  typeFichier: 'transactions',
  cle: 'tx_ANTOINE_2026-05',
  dateDonnees: '2026-05',
  cheminFichier: 'data/transactions/ANTOINE_2026-05.xlsx',
  nbLignes: 2_984,
  dateExecution: '2026-05-31 17:09:55',
  fichierDisponible: true
}];