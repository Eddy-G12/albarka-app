import React, { useMemo, useState } from 'react';
import { twMerge } from 'tailwind-merge';
import { ChevronDownIcon, ChevronUpIcon, DownloadIcon, SearchIcon } from 'lucide-react';
import { Button } from './ui/Button';
import { EtatVide, Squelette } from './ui/States';

export interface Colonne<T> {
  cle: string;
  entete: string;
  numerique?: boolean;
  largeur?: string;
  valeur?: (ligne: T) => string | number;
  rendu?: (ligne: T) => React.ReactNode;
  triable?: boolean;
}

interface DataTableProps<T> {
  colonnes: Colonne<T>[];
  lignes: T[];
  cleLigne: (ligne: T, index: number) => string;
  recherche?: boolean;
  placeholderRecherche?: string;
  parPage?: number;
  chargement?: boolean;
  messageVide?: string;
  onExport?: () => void;
  ligneSurlignee?: (ligne: T) => boolean;
  compact?: boolean;
}

export function DataTable<T>({
  colonnes,
  lignes,
  cleLigne,
  recherche = false,
  placeholderRecherche = 'Rechercher…',
  parPage = 12,
  chargement = false,
  messageVide = 'Aucune donnée pour ces filtres.',
  onExport,
  ligneSurlignee,
  compact = false
}: DataTableProps<T>) {
  const [terme, setTerme] = useState('');
  const [tri, setTri] = useState<{cle: string;sens: 'asc' | 'desc';} | null>(null);
  const [page, setPage] = useState(0);

  const valeurBrute = (ligne: T, colonne: Colonne<T>) =>
  colonne.valeur ? colonne.valeur(ligne) : (ligne as Record<string, unknown>)[colonne.cle] as string | number;

  const filtrees = useMemo(() => {
    if (!terme.trim()) return lignes;
    const t = terme.trim().toLowerCase();
    return lignes.filter((ligne) =>
    colonnes.some((colonne) => String(valeurBrute(ligne, colonne) ?? '').toLowerCase().includes(t))
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lignes, terme, colonnes]);

  const triees = useMemo(() => {
    if (!tri) return filtrees;
    const colonne = colonnes.find((c) => c.cle === tri.cle);
    if (!colonne) return filtrees;
    return [...filtrees].sort((a, b) => {
      const va = valeurBrute(a, colonne);
      const vb = valeurBrute(b, colonne);
      const cmp =
      typeof va === 'number' && typeof vb === 'number' ?
      va - vb :
      String(va ?? '').localeCompare(String(vb ?? ''), 'fr');
      return tri.sens === 'asc' ? cmp : -cmp;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtrees, tri, colonnes]);

  const nbPages = Math.max(1, Math.ceil(triees.length / parPage));
  const pageCourante = Math.min(page, nbPages - 1);
  const visibles = triees.slice(pageCourante * parPage, (pageCourante + 1) * parPage);

  const basculerTri = (cle: string) => {
    setPage(0);
    setTri((courant) =>
    courant?.cle === cle ?
    { cle, sens: courant.sens === 'asc' ? 'desc' : 'asc' } :
    { cle, sens: 'desc' }
    );
  };

  if (chargement) return <Squelette lignes={6} hauteur="h-8" />;

  return (
    <div>
      {(recherche || onExport) &&
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {recherche ?
        <div className="relative w-full max-w-xs">
              <SearchIcon
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-albarka-muted"
            aria-hidden />
          
              <input
            value={terme}
            onChange={(e) => {
              setTerme(e.target.value);
              setPage(0);
            }}
            placeholder={placeholderRecherche}
            aria-label="Rechercher dans le tableau"
            className="h-9 w-full rounded-md border border-albarka-border bg-white pl-9 pr-3 text-sm placeholder:text-albarka-muted/70" />
          
            </div> :

        <span />
        }
          {onExport &&
        <Button taille="sm" icone={<DownloadIcon className="h-3.5 w-3.5" />} onClick={onExport}>
              Exporter
            </Button>
        }
        </div>
      }

      {triees.length === 0 ?
      <EtatVide titre="Rien à afficher" message={messageVide} /> :

      <>
          <div className="albarka-scroll overflow-x-auto rounded-md border border-albarka-border">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-albarka-bg">
                  {colonnes.map((colonne) => {
                  const actif = tri?.cle === colonne.cle;
                  const triable = colonne.triable !== false;
                  return (
                    <th
                      key={colonne.cle}
                      scope="col"
                      style={{ width: colonne.largeur }}
                      className={twMerge(
                        'border-b border-albarka-border px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-albarka-muted',
                        colonne.numerique ? 'text-right' : 'text-left'
                      )}>
                      
                        {triable ?
                      <button
                        type="button"
                        onClick={() => basculerTri(colonne.cle)}
                        className={twMerge(
                          'inline-flex items-center gap-1 transition-colors duration-150 ease-out hover:text-albarka-black',
                          actif && 'text-albarka-black'
                        )}>
                        
                            {colonne.entete}
                            {actif && (
                        tri?.sens === 'asc' ?
                        <ChevronUpIcon className="h-3 w-3" aria-hidden /> :

                        <ChevronDownIcon className="h-3 w-3" aria-hidden />)
                        }
                          </button> :

                      colonne.entete
                      }
                      </th>);

                })}
                </tr>
              </thead>
              <tbody>
                {visibles.map((ligne, index) =>
              <tr
                key={cleLigne(ligne, index)}
                className={twMerge(
                  'border-b border-albarka-border/70 last:border-0',
                  index % 2 === 1 && 'bg-albarka-bg/40',
                  ligneSurlignee?.(ligne) && 'bg-albarka-yellow-soft'
                )}>
                
                    {colonnes.map((colonne) =>
                <td
                  key={colonne.cle}
                  className={twMerge(
                    'px-3 text-albarka-ink',
                    compact ? 'py-1.5' : 'py-2.5',
                    colonne.numerique && 'num text-right'
                  )}>
                  
                        {colonne.rendu ? colonne.rendu(ligne) : String(valeurBrute(ligne, colonne) ?? '—')}
                      </td>
                )}
                  </tr>
              )}
              </tbody>
            </table>
          </div>

          {nbPages > 1 &&
        <div className="mt-3 flex items-center justify-between text-xs text-albarka-muted">
              <span className="num">
                {pageCourante * parPage + 1}–{Math.min((pageCourante + 1) * parPage, triees.length)} sur{' '}
                {triees.length}
              </span>
              <div className="flex items-center gap-2">
                <Button
              taille="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={pageCourante === 0}>
              
                  Précédent
                </Button>
                <Button
              taille="sm"
              onClick={() => setPage((p) => Math.min(nbPages - 1, p + 1))}
              disabled={pageCourante >= nbPages - 1}>
              
                  Suivant
                </Button>
              </div>
            </div>
        }
        </>
      }
    </div>);

}