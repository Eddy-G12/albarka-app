import React, { useState } from 'react';
import { toast } from 'sonner';
import { DownloadIcon, SearchIcon, Trash2Icon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Section } from '../components/ui/Section';
import { Button } from '../components/ui/Button';
import { Champ, Select } from '../components/ui/Field';
import { BadgeNeutre } from '../components/StatusBadge';
import { BlocAsync, EtatVide, Squelette } from '../components/ui/States';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { useAuth } from '../contexts/AuthContext';
import { useAsync } from '../hooks/useAsync';
import { getImports, supprimerImport } from '../services/gestion';
import type { TypeFichier } from '../types';
import { formatNombre, labelDate, labelDateHeure } from '../utils/format';

const LIBELLE_TYPE: Record<TypeFichier, string> = {
  qr_code: 'QR Code',
  transactions: 'Transactions',
  comparatif: 'Comparatif'
};

export function Historique() {
  const { peutSupprimer } = useAuth();
  const [type, setType] = useState<TypeFichier | 'tous'>('tous');
  const [recherche, setRecherche] = useState('');
  const [visibles, setVisibles] = useState(5);
  const [aSupprimer, setASupprimer] = useState<number | null>(null);
  const [version, setVersion] = useState(0);

  const imports = useAsync(() => getImports({ type, recherche }), [type, recherche, version]);

  return (
    <div>
      <PageHeader
        titre="Historique des traitements"
        description="Tous les traitements exécutés, avec le classeur Excel correspondant lorsqu'il est encore présent sur le disque."
        filtres={
        <>
            <Champ label="Type de fichier" htmlFor="type-fichier" className="w-48">
              <Select
              id="type-fichier"
              value={type}
              onChange={(e) => {
                setType(e.target.value as TypeFichier | 'tous');
                setVisibles(5);
              }}>
              
                <option value="tous">Tous les types</option>
                <option value="qr_code">QR Code</option>
                <option value="transactions">Transactions</option>
                <option value="comparatif">Comparatif</option>
              </Select>
            </Champ>
            <div className="relative w-full max-w-xs">
              <label htmlFor="recherche-historique" className="mb-1.5 block text-2xs font-semibold uppercase tracking-wide text-albarka-muted">
                Recherche
              </label>
              <SearchIcon
              className="pointer-events-none absolute left-3 top-[34px] h-4 w-4 text-albarka-muted"
              aria-hidden />
            
              <input
              id="recherche-historique"
              value={recherche}
              onChange={(e) => {
                setRecherche(e.target.value);
                setVisibles(5);
              }}
              placeholder="Clé ou chemin du fichier"
              className="h-10 w-full rounded-md border border-albarka-border bg-white pl-9 pr-3 text-sm placeholder:text-albarka-muted/70" />
            
            </div>
          </>
        } />
      

      <Section>
        <BlocAsync etat={imports} squelette={<Squelette lignes={5} hauteur="h-14" />}>
          {(lignes) =>
          lignes.length === 0 ?
          <EtatVide
            titre="Aucun traitement"
            message="Aucun traitement ne correspond à ce type ou à cette recherche." /> :


          <div>
                <ul className="space-y-2">
                  {lignes.slice(0, visibles).map((ligne) =>
              <li
                key={ligne.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-albarka-border px-4 py-3">
                
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <BadgeNeutre ton="accent">{LIBELLE_TYPE[ligne.typeFichier as TypeFichier] ?? ligne.typeFichier}</BadgeNeutre>
                          <span className="truncate text-sm font-medium text-albarka-black">
                            {ligne.cle}
                          </span>
                        </div>
                        <p className="num mt-1 text-2xs text-albarka-muted">
                          Données du {labelDate(ligne.dateDonnees ?? '')} ·{' '}
                          {formatNombre(ligne.nbLignes ?? 0)} lignes · exécuté le{' '}
                          {labelDateHeure(ligne.dateExecution)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {ligne.fichierDisponible ?
                  <Button
                    taille="sm"
                    icone={<DownloadIcon className="h-3.5 w-3.5" />}
                    onClick={() => toast.success('Téléchargement du classeur lancé.')}>
                    
                            Télécharger
                          </Button> :

                  <span className="text-2xs text-albarka-muted">Fichier absent du disque</span>
                  }
                        {peutSupprimer &&
                  <Button
                    taille="sm"
                    variante="danger"
                    icone={<Trash2Icon className="h-3.5 w-3.5" />}
                    onClick={() => setASupprimer(ligne.id)}>
                    
                            Supprimer
                          </Button>
                  }
                      </div>
                    </li>
              )}
                </ul>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {visibles < lignes.length &&
              <Button onClick={() => setVisibles((v) => v + 10)}>
                      Voir plus (10 traitements)
                    </Button>
              }
                  {visibles > 5 &&
              <Button variante="fantome" onClick={() => setVisibles(5)}>
                      Replier
                    </Button>
              }
                  <span className="num text-xs text-albarka-muted">
                    {Math.min(visibles, lignes.length)} sur {lignes.length}
                  </span>
                </div>
              </div>

          }
        </BlocAsync>
      </Section>

      <ConfirmDialog
        ouvert={aSupprimer !== null}
        titre="Supprimer cet enregistrement ?"
        message="Le traitement disparaîtra de l'historique."
        note="Le classeur Excel reste intact sur le disque — seule la ligne en base est supprimée."
        onAnnuler={() => setASupprimer(null)}
        onConfirmer={async () => {
          if (aSupprimer !== null) {
            await supprimerImport(aSupprimer);
            toast.success('Enregistrement supprimé de la base.');
            setVersion((v) => v + 1);
          }
          setASupprimer(null);
        }} />
      
    </div>);

}