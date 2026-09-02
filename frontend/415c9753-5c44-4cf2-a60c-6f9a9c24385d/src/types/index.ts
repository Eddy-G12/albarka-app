export type Role = 'super_admin' | 'admin' | 'commercial';

export interface Utilisateur {
  id: number;
  username: string;
  nom: string;
  role: Role;
  actif: boolean;
  dsmName?: string;
  createdAt: string;
}

export interface Commercial {
  id: number;
  utilisateurId: number;
  dsmName: string;
  telephone: string;
  zone: string;
  actif: boolean;
  alias: string | null;
}

export type QrStatut = 'actif' | 'risque' | 'non_utilise' | 'sans_qr';

export interface QrAgent {
  posMsisdn: string;
  posName: string;
  dsmName: string;
  segmentGroup: string;
  region: string;
  town: string;
  statut: QrStatut;
  lastQrCoDate: string | null;
  activeDeployed: number | null;
  active30: number;
}

export interface Pos {
  id: number;
  acceptorId: string;
  agentMsisdn: string;
  agentName: string;
}

export interface CashflowPos {
  posId: number;
  acceptorId: string;
  agentName: string;
  agentMsisdn: string;
  mois: string;
  cashIn: number;
  cashOut: number;
}

export interface TransactionMomo {
  commercialId: number;
  mois: string;
  cashIn: number;
  cashOut: number;
  nbTransactions: number;
}

export type TypeOp = 'appro' | 'destockage';

export interface ApproEntry {
  id: number;
  commercialId: number;
  dateOp: string;
  typeOp: TypeOp;
  nbOps: number;
  montant: number;
  sourceFichier: string;
}

export interface PointTouche {
  commercialId: number;
  dateOp: string;
  nbPoints: number;
}

export interface ClientServi {
  commercialId: number;
  dateOp: string;
  nomContrepartie: string;
  msisdn: string;
  nbTransactions: number;
}

export interface Portefeuille {
  id: number;
  commercialId: number;
  nom: string;
  dateImport: string;
  nbClients: number;
}

export interface ClientPortefeuille {
  id: number;
  portefeuilleId: number;
  nom: string;
  telephone: string;
  localite: string;
}

export interface Parrainage {
  personne: string;
  dateOp: string;
  nb: number;
}

export interface SuiviPersonne {
  id: number;
  commercialId: number;
  nomPersonne: string;
  montant: number;
  dateHeure: string;
}

export type TypeFichier = 'qr_code' | 'transactions' | 'comparatif';

export interface ImportRecord {
  id: number;
  typeFichier: TypeFichier;
  cle: string;
  dateDonnees: string;
  cheminFichier: string;
  nbLignes: number;
  dateExecution: string;
  fichierDisponible: boolean;
}

export interface Seuil {
  id: number;
  typeFlux: 'cash_in' | 'cash_out';
  valeur: number;
  mois: string | null;
  createdBy: string;
  createdAt: string;
}

export interface ReactiviteIndicateur {
  commercialId: number;
  dsmName: string;
  nbTransactions: number;
  joursActifs: number;
  txParJour: number;
  clientsParJour: number;
  tempsMortMedian: number | null;
  tempsMortMax: number | null;
  tempsRechargeMedian: number | null;
  tempsRechargeMin: number | null;
}

export interface RangAnonymise {
  position: number;
  libelle: string;
  cashIn: number;
  cashOut: number;
  estMoi: boolean;
}