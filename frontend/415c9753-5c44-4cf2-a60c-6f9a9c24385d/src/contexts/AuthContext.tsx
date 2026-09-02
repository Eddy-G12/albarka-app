import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { Commercial, Utilisateur } from '../types';
import { connexion, effacerSession, lireSession, sauverSession } from '../services/auth';
import { getCommerciaux } from '../services/gestion';
import { store } from '../services/store';

interface ValeurAuth {
  utilisateur: Utilisateur | null;
  commercial: Commercial | null;
  connecte: boolean;
  seConnecter: (username: string, motDePasse: string) => Promise<void>;
  seDeconnecter: () => void;
  peutDeposer: boolean;
  peutSaisir: boolean;
  peutSupprimer: boolean;
  estCommercial: boolean;
}

const AuthContext = createContext<ValeurAuth | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(
    () => lireSession()?.utilisateur ?? null,
  );
  const [commercial, setCommercial] = useState<Commercial | null>(null);

  // Charge la liste des commerciaux depuis l'API dès qu'un utilisateur est connecté
  // pour pouvoir résoudre le commercial lié au compte connecté.
  useEffect(() => {
    if (!utilisateur) {
      setCommercial(null);
      store.commerciaux = [];
      return;
    }
    if (utilisateur.role !== 'commercial') {
      setCommercial(null);
      return;
    }
    getCommerciaux()
      .then((list) => {
        store.commerciaux = list;
        const found = list.find((c) => c.utilisateurId === utilisateur.id) ?? null;
        setCommercial(found);
      })
      .catch(() => {
        // En cas d'erreur réseau, on laisse commercial à null
      });
  }, [utilisateur]);

  const seConnecter = useCallback(async (username: string, motDePasse: string) => {
    const resultat = await connexion(username, motDePasse);
    sauverSession(resultat);
    setUtilisateur(resultat.utilisateur);
  }, []);

  const seDeconnecter = useCallback(() => {
    effacerSession();
    setUtilisateur(null);
    setCommercial(null);
  }, []);

  const valeur = useMemo<ValeurAuth>(() => {
    const role = utilisateur?.role;
    return {
      utilisateur,
      commercial,
      connecte:       Boolean(utilisateur),
      seConnecter,
      seDeconnecter,
      peutDeposer:    role === 'super_admin',
      peutSaisir:     role === 'super_admin',
      peutSupprimer:  role === 'super_admin',
      estCommercial:  role === 'commercial',
    };
  }, [utilisateur, commercial, seConnecter, seDeconnecter]);

  return <AuthContext.Provider value={valeur}>{children}</AuthContext.Provider>;
}

export function useAuth(): ValeurAuth {
  const valeur = useContext(AuthContext);
  if (!valeur) throw new Error('useAuth doit être utilisé dans AuthProvider');
  return valeur;
}
