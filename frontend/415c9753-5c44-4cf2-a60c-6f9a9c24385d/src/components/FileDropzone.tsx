import React, { useCallback, useRef, useState } from 'react';
import { twMerge } from 'tailwind-merge';
import {
  CheckCircle2Icon,
  DownloadIcon,
  FileIcon,
  UploadCloudIcon,
  XIcon } from
'lucide-react';
import { Button } from './ui/Button';
import { Select } from './ui/Field';

export interface FichierImporte {
  id: string;
  nom: string;
  taille: number;
  progression: number;
  statut: 'en_cours' | 'termine' | 'erreur';
  commercial: string | null;
  nbLignes: number;
  message?: string;
}

interface FileDropzoneProps {
  accept?: string;
  multiple?: boolean;
  legende: string;
  commerciaux?: {dsmName: string;alias: string | null;}[];
  onTermine?: (fichier: FichierImporte) => void;
  actionsGlobales?: React.ReactNode;
}

function detecterCommercial(nom: string, dsms: string[]): string | null {
  const majuscule = nom.toUpperCase();
  return dsms.find((dsm) => majuscule.includes(dsm)) ?? null;
}

export function FileDropzone({
  accept,
  multiple = true,
  legende,
  commerciaux,
  onTermine,
  actionsGlobales
}: FileDropzoneProps) {
  const [survol, setSurvol] = useState(false);
  const [fichiers, setFichiers] = useState<FichierImporte[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const traiter = useCallback(
    (liste: FileList | null) => {
      if (!liste?.length) return;
      const dsms = commerciaux?.map((c) => c.dsmName) ?? [];
      Array.from(liste).forEach((fichier, index) => {
        const id = `${fichier.name}-${Date.now()}-${index}`;
        const entree: FichierImporte = {
          id,
          nom: fichier.name,
          taille: fichier.size,
          progression: 0,
          statut: 'en_cours',
          commercial: detecterCommercial(fichier.name, dsms),
          nbLignes: 0
        };
        setFichiers((courant) => [...courant, entree]);

        let progression = 0;
        const timer = window.setInterval(() => {
          progression = Math.min(100, progression + 12 + Math.random() * 18);
          setFichiers((courant) =>
          courant.map((f) => f.id === id ? { ...f, progression: Math.round(progression) } : f)
          );
          if (progression >= 100) {
            window.clearInterval(timer);
            const nbLignes = 800 + Math.floor(Math.random() * 5_200);
            setFichiers((courant) =>
            courant.map((f) =>
            f.id === id ?
            {
              ...f,
              statut: 'termine',
              nbLignes,
              message: 'Traitement terminé, classeur Excel généré.'
            } :
            f
            )
            );
            onTermine?.({ ...entree, progression: 100, statut: 'termine', nbLignes });
          }
        }, 260);
      });
    },
    [commerciaux, onTermine]
  );

  const retirer = (id: string) => setFichiers((courant) => courant.filter((f) => f.id !== id));

  const termines = fichiers.filter((f) => f.statut === 'termine');

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setSurvol(true);
        }}
        onDragLeave={() => setSurvol(false)}
        onDrop={(e) => {
          e.preventDefault();
          setSurvol(false);
          traiter(e.dataTransfer.files);
        }}
        className={twMerge(
          'rounded-lg border border-dashed px-6 py-8 text-center transition-colors duration-150 ease-out',
          survol ?
          'border-albarka-yellow bg-albarka-yellow-soft' :
          'border-albarka-border bg-albarka-bg/60'
        )}>
        
        <UploadCloudIcon className="mx-auto mb-2 h-6 w-6 text-albarka-muted" aria-hidden />
        <p className="text-sm font-medium text-albarka-black">
          Glissez vos fichiers ici ou parcourez votre poste
        </p>
        <p className="mx-auto mt-1 max-w-md text-xs text-albarka-muted">{legende}</p>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="sr-only"
          onChange={(e) => {
            traiter(e.target.files);
            e.target.value = '';
          }} />
        
        <Button
          variante="primaire"
          taille="sm"
          className="mt-4"
          onClick={() => inputRef.current?.click()}>
          
          Choisir des fichiers
        </Button>
      </div>

      {fichiers.length > 0 &&
      <ul className="mt-4 space-y-2">
          {fichiers.map((fichier) =>
        <li
          key={fichier.id}
          className="rounded-md border border-albarka-border bg-white px-3 py-2.5">
          
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  {fichier.statut === 'termine' ?
              <CheckCircle2Icon className="h-4 w-4 shrink-0 text-statut-actif" aria-hidden /> :

              <FileIcon className="h-4 w-4 shrink-0 text-albarka-muted" aria-hidden />
              }
                  <span className="truncate text-sm text-albarka-black">{fichier.nom}</span>
                  <span className="num shrink-0 text-2xs text-albarka-muted">
                    {(fichier.taille / 1024).toFixed(0)} Ko
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {commerciaux &&
              <Select
                aria-label={`Commercial associé à ${fichier.nom}`}
                className="h-8 w-44 text-xs"
                value={fichier.commercial ?? ''}
                onChange={(e) =>
                setFichiers((courant) =>
                courant.map((f) =>
                f.id === fichier.id ? { ...f, commercial: e.target.value || null } : f
                )
                )
                }>
                
                      <option value="">Commercial non détecté</option>
                      {commerciaux.map((c) =>
                <option key={c.dsmName} value={c.dsmName}>
                          {c.dsmName}
                          {c.alias ? ` · ${c.alias}` : ' · sans alias'}
                        </option>
                )}
                    </Select>
              }
                  {fichier.statut === 'termine' &&
              <Button taille="sm" icone={<DownloadIcon className="h-3.5 w-3.5" />}>
                      Classeur
                    </Button>
              }
                  <button
                type="button"
                aria-label={`Retirer ${fichier.nom}`}
                onClick={() => retirer(fichier.id)}
                className="rounded p-1 text-albarka-muted transition-colors duration-150 ease-out hover:bg-albarka-bg hover:text-albarka-black">
                
                    <XIcon className="h-4 w-4" aria-hidden />
                  </button>
                </div>
              </div>
              {fichier.statut === 'en_cours' ?
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-albarka-bg">
                  <div
              className="h-full rounded-full bg-albarka-yellow transition-[width] duration-200 ease-out"
              style={{ width: `${fichier.progression}%` }} />
            
                </div> :

          <p className="num mt-1.5 text-2xs text-albarka-muted">
                  {fichier.nbLignes.toLocaleString('fr-FR')} lignes traitées ·{' '}
                  {fichier.commercial ?? 'commercial à confirmer'}
                </p>
          }
            </li>
        )}
        </ul>
      }

      {termines.length >= 2 &&
      <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button variante="secondaire" taille="sm" icone={<DownloadIcon className="h-3.5 w-3.5" />}>
            Télécharger le ZIP global ({termines.length} classeurs)
          </Button>
          {actionsGlobales}
        </div>
      }
    </div>);

}