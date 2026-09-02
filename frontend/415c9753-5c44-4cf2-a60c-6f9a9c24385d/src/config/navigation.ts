import type { LucideIcon } from 'lucide-react';
import {
  ArrowLeftRightIcon,
  BarChart3Icon,
  ClipboardListIcon,
  DatabaseIcon,
  FileSpreadsheetIcon,
  GaugeIcon,
  HistoryIcon,
  HomeIcon,
  LayoutDashboardIcon,
  QrCodeIcon,
  ScanLineIcon,
  SettingsIcon,
  TimerIcon,
  UserRoundCheckIcon,
  UsersIcon,
  WalletIcon } from
'lucide-react';
import type { Role } from '../types';

export interface EntreeNavigation {
  chemin: string;
  libelle: string;
  description: string;
  groupe: 'Pilotage' | 'Analyse' | 'Import' | 'Saisie' | 'Gestion';
  icone: LucideIcon;
  roles: Role[];
}

export const NAVIGATION: EntreeNavigation[] = [
{
  chemin: '/',
  libelle: 'Accueil',
  description: 'Vos modules disponibles et leur rôle dans le pilotage du réseau.',
  groupe: 'Pilotage',
  icone: HomeIcon,
  roles: ['super_admin', 'admin', 'commercial']
},
{
  chemin: '/dashboard',
  libelle: 'Dashboard Global',
  description: 'Vue consolidée cash, réactivité, QR Code et appros du réseau.',
  groupe: 'Pilotage',
  icone: LayoutDashboardIcon,
  roles: ['super_admin', 'admin']
},
{
  chemin: '/mon-dashboard',
  libelle: 'Mon Dashboard',
  description: 'Votre périmètre QR Code, vos cash in/out et votre rang anonymisé.',
  groupe: 'Pilotage',
  icone: GaugeIcon,
  roles: ['commercial']
},
{
  chemin: '/cash-flow',
  libelle: 'Cash Flow',
  description: 'Classements POS, alertes seuil et comparaison multi-mois depuis le SAE MTN.',
  groupe: 'Analyse',
  icone: BarChart3Icon,
  roles: ['super_admin', 'admin']
},
{
  chemin: '/dashboard-qr',
  libelle: 'Dashboard QR Code',
  description: 'Répartition des agents par statut, segment et DSM à une date de référence.',
  groupe: 'Analyse',
  icone: QrCodeIcon,
  roles: ['super_admin', 'admin']
},
{
  chemin: '/etude-comparative',
  libelle: 'Étude Comparative',
  description: 'Comparaison de deux dates QR Code et mouvements détaillés des agents.',
  groupe: 'Analyse',
  icone: ArrowLeftRightIcon,
  roles: ['super_admin', 'admin']
},
{
  chemin: '/appro',
  libelle: 'Appro / Destockage',
  description: 'Approvisionnements et destockages par commercial, mois et journée.',
  groupe: 'Analyse',
  icone: WalletIcon,
  roles: ['super_admin', 'admin', 'commercial']
},
{
  chemin: '/mom',
  libelle: 'Comparaisons MoM',
  description: 'Évolution mois vs mois-1 sur le cash, les appros et le QR Code.',
  groupe: 'Analyse',
  icone: TimerIcon,
  roles: ['super_admin', 'admin', 'commercial']
},
{
  chemin: '/reactivite',
  libelle: 'Réactivité Commerciale',
  description: 'Temps morts, temps de recharge et rythme quotidien par commercial.',
  groupe: 'Analyse',
  icone: ScanLineIcon,
  roles: ['super_admin', 'admin']
},
{
  chemin: '/transactions',
  libelle: 'Transactions',
  description: 'Dépôt des CSV bruts MTN, points touchés et clients servis.',
  groupe: 'Import',
  icone: FileSpreadsheetIcon,
  roles: ['super_admin']
},
{
  chemin: '/suivi-qr',
  libelle: 'Suivi QR Code',
  description: 'Dépôt du fichier QR, classification des agents et rapport multi-onglets.',
  groupe: 'Import',
  icone: QrCodeIcon,
  roles: ['super_admin']
},
{
  chemin: '/portefeuilles',
  libelle: 'Portefeuilles',
  description: 'Import des portefeuilles clients, consultation et taux de couverture.',
  groupe: 'Import',
  icone: DatabaseIcon,
  roles: ['super_admin', 'admin']
},
{
  chemin: '/momo-app',
  libelle: 'MoMo App',
  description: 'Saisie et suivi des parrainages par personne et par jour.',
  groupe: 'Saisie',
  icone: UserRoundCheckIcon,
  roles: ['super_admin']
},
{
  chemin: '/suivi-personnes',
  libelle: 'Suivi Personnes',
  description: 'Montants suivis par commercial sur les personnes spécialement suivies.',
  groupe: 'Saisie',
  icone: ClipboardListIcon,
  roles: ['super_admin']
},
{
  chemin: '/historique',
  libelle: 'Historique',
  description: 'Tous les traitements exécutés, avec téléchargement des classeurs.',
  groupe: 'Gestion',
  icone: HistoryIcon,
  roles: ['super_admin', 'admin']
},
{
  chemin: '/administration',
  libelle: 'Administration',
  description: 'Comptes, commerciaux, aliases CSV et seuils cash in / cash out.',
  groupe: 'Gestion',
  icone: SettingsIcon,
  roles: ['super_admin']
}];


export const ICONE_UTILISATEURS = UsersIcon;

export function navigationPourRole(role: Role): EntreeNavigation[] {
  return NAVIGATION.filter((entree) => entree.roles.includes(role));
}

export function pageAutorisee(chemin: string, role: Role): boolean {
  return NAVIGATION.some((e) => e.chemin === chemin && e.roles.includes(role));
}