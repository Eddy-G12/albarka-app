import type { Commercial, Seuil, Utilisateur } from '../types';

export const COMPTES: {username: string;motDePasse: string;}[] = [
{ username: 'giovanni', motDePasse: 'sadmin123' },
{ username: 'theo', motDePasse: 'admin123' },
{ username: 'parfait', motDePasse: 'parfait123' },
{ username: 'stephane', motDePasse: 'stephane123' },
{ username: 'antoine', motDePasse: 'antoine123' },
{ username: 'erve', motDePasse: 'erve123' },
{ username: 'ewane', motDePasse: 'ewane123' },
{ username: 'franck', motDePasse: 'franck123' },
{ username: 'prosper', motDePasse: 'prosper123' },
{ username: 'cesaire', motDePasse: 'cesaire123' }];


export const UTILISATEURS: Utilisateur[] = [
{
  id: 1,
  username: 'giovanni',
  nom: 'Giovanni Mbarga',
  role: 'super_admin',
  actif: true,
  createdAt: '2025-11-04'
},
{
  id: 2,
  username: 'theo',
  nom: 'Théo Nkoulou',
  role: 'admin',
  actif: true,
  createdAt: '2025-11-04'
},
{
  id: 3,
  username: 'parfait',
  nom: 'Parfait Ndongo',
  role: 'commercial',
  actif: true,
  dsmName: 'PARFAIT',
  createdAt: '2025-11-12'
},
{
  id: 4,
  username: 'stephane',
  nom: 'Stéphane Onana',
  role: 'commercial',
  actif: true,
  dsmName: 'STEPHANE',
  createdAt: '2025-11-12'
},
{
  id: 5,
  username: 'antoine',
  nom: 'Antoine Bello',
  role: 'commercial',
  actif: true,
  dsmName: 'ANTOINE',
  createdAt: '2025-11-12'
},
{
  id: 6,
  username: 'erve',
  nom: 'Ervé Tchoumi',
  role: 'commercial',
  actif: true,
  dsmName: 'ERVE',
  createdAt: '2025-12-02'
},
{
  id: 7,
  username: 'ewane',
  nom: 'Ewane Dipita',
  role: 'commercial',
  actif: true,
  dsmName: 'EWANE',
  createdAt: '2025-12-02'
},
{
  id: 8,
  username: 'franck',
  nom: 'Franck Essomba',
  role: 'commercial',
  actif: true,
  dsmName: 'FRANCK',
  createdAt: '2026-01-15'
},
{
  id: 9,
  username: 'prosper',
  nom: 'Prosper Ateba',
  role: 'commercial',
  actif: true,
  dsmName: 'PROSPER',
  createdAt: '2026-01-15'
},
{
  id: 10,
  username: 'cesaire',
  nom: 'Césaire Ngoma',
  role: 'commercial',
  actif: false,
  dsmName: 'CESAIRE',
  createdAt: '2026-02-03'
}];


export const COMMERCIAUX: Commercial[] = [
{
  id: 1,
  utilisateurId: 3,
  dsmName: 'PARFAIT',
  telephone: '237677120045',
  zone: 'Douala Littoral',
  actif: true,
  alias: 'ALBARKA 135'
},
{
  id: 2,
  utilisateurId: 4,
  dsmName: 'STEPHANE',
  telephone: '237699441203',
  zone: 'Yaoundé Centre',
  actif: true,
  alias: 'ALBARKA 85'
},
{
  id: 3,
  utilisateurId: 5,
  dsmName: 'ANTOINE',
  telephone: '237655903318',
  zone: 'Douala Bonabéri',
  actif: true,
  alias: 'ALBARKA 72'
},
{
  id: 4,
  utilisateurId: 6,
  dsmName: 'ERVE',
  telephone: '237678225614',
  zone: 'Ouest Bafoussam',
  actif: true,
  alias: 'ALBARKA 89'
},
{
  id: 5,
  utilisateurId: 7,
  dsmName: 'EWANE',
  telephone: '237691770082',
  zone: 'Sud-Ouest Buéa',
  actif: true,
  alias: 'ALBARKA 71'
},
{
  id: 6,
  utilisateurId: 8,
  dsmName: 'FRANCK',
  telephone: '237673558940',
  zone: 'Nord Garoua',
  actif: true,
  alias: null
},
{
  id: 7,
  utilisateurId: 9,
  dsmName: 'PROSPER',
  telephone: '237696110274',
  zone: 'Est Bertoua',
  actif: true,
  alias: null
},
{
  id: 8,
  utilisateurId: 10,
  dsmName: 'CESAIRE',
  telephone: '237677884411',
  zone: 'Adamaoua Ngaoundéré',
  actif: false,
  alias: null
}];


export const ALIASES_PAR_DEFAUT: Record<string, string | null> = {
  PARFAIT: 'ALBARKA 135',
  STEPHANE: 'ALBARKA 85',
  ANTOINE: 'ALBARKA 72',
  ERVE: 'ALBARKA 89',
  EWANE: 'ALBARKA 71',
  FRANCK: null,
  PROSPER: null,
  CESAIRE: null
};

export const SEUILS: Seuil[] = [
{
  id: 1,
  typeFlux: 'cash_in',
  valeur: 45_000,
  mois: null,
  createdBy: 'giovanni',
  createdAt: '2026-03-11'
},
{
  id: 2,
  typeFlux: 'cash_out',
  valeur: 30_000,
  mois: null,
  createdBy: 'giovanni',
  createdAt: '2026-03-11'
},
{
  id: 3,
  typeFlux: 'cash_in',
  valeur: 52_000,
  mois: '2026-08',
  createdBy: 'giovanni',
  createdAt: '2026-08-02'
}];


export function commercialParId(id: number): Commercial | undefined {
  return COMMERCIAUX.find((c) => c.id === id);
}

export function commercialParDsm(dsmName: string): Commercial | undefined {
  return COMMERCIAUX.find((c) => c.dsmName === dsmName);
}