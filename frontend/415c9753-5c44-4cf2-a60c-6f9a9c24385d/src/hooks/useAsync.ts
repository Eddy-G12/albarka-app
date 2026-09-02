import { useCallback, useEffect, useRef, useState } from 'react';

export interface EtatAsync<T> {
  donnees: T | null;
  chargement: boolean;
  erreur: string | null;
  recharger: () => void;
}

/**
 * Petit chargeur de données : chaque écran expose ainsi ses états
 * chargement / erreur / vide sans dupliquer la logique.
 */
export function useAsync<T>(chargeur: () => Promise<T>, deps: unknown[]): EtatAsync<T> {
  const [donnees, setDonnees] = useState<T | null>(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [compteur, setCompteur] = useState(0);
  const actif = useRef(true);
  const refChargeur = useRef(chargeur);
  refChargeur.current = chargeur;

  useEffect(() => {
    actif.current = true;
    setChargement(true);
    setErreur(null);
    refChargeur.
    current().
    then((resultat) => {
      if (actif.current) setDonnees(resultat);
    }).
    catch((e: unknown) => {
      if (actif.current) {
        setErreur(e instanceof Error ? e.message : 'Impossible de charger les données.');
      }
    }).
    finally(() => {
      if (actif.current) setChargement(false);
    });
    return () => {
      actif.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, compteur]);

  const recharger = useCallback(() => setCompteur((c) => c + 1), []);

  return { donnees, chargement, erreur, recharger };
}