import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { DATE_QR_COURANTE, MOIS_COURANT } from '../data/seed';
import { getDatesQr } from '../services/qr';

interface ValeurFiltres {
  moisCash: string;
  moisAppro: string;
  dateQr: string;
  setMoisCash: (mois: string) => void;
  setMoisAppro: (mois: string) => void;
  setDateQr: (date: string) => void;
}

const FiltresContext = createContext<ValeurFiltres | null>(null);

/** Filtres partagés entre les sections d'une même page (mois cash, mois appro, date QR). */
export function FiltresProvider({ children }: {children: React.ReactNode;}) {
  const [moisCash, setMoisCash] = useState(MOIS_COURANT);
  const [moisAppro, setMoisAppro] = useState(MOIS_COURANT);
  const [dateQr, setDateQr] = useState(DATE_QR_COURANTE);

  // Charge la dernière date QR disponible depuis l'API au démarrage
  useEffect(() => {
    getDatesQr()
      .then((dates) => { if (dates.length > 0) setDateQr(dates[0]); })
      .catch(() => { /* garde le fallback de seed.ts */ });
  }, []);

  const valeur = useMemo(
    () => ({ moisCash, moisAppro, dateQr, setMoisCash, setMoisAppro, setDateQr }),
    [moisCash, moisAppro, dateQr]
  );

  return <FiltresContext.Provider value={valeur}>{children}</FiltresContext.Provider>;
}

export function useFiltres(): ValeurFiltres {
  const valeur = useContext(FiltresContext);
  if (!valeur) throw new Error('useFiltres doit être utilisé dans FiltresProvider');
  return valeur;
}