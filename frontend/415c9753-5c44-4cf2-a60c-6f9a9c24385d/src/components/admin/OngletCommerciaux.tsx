import React, { useState } from 'react';
import { toast } from 'sonner';
import { Section, TitreBloc } from '../ui/Section';
import { Button } from '../ui/Button';
import { Champ, Input, Select } from '../ui/Field';
import { DataTable } from '../DataTable';
import { BadgeNeutre } from '../StatusBadge';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { BlocAsync, Squelette } from '../ui/States';
import { useAsync } from '../../hooks/useAsync';
import { getCommerciaux, majCommercial } from '../../services/gestion';
import { ALIASES_PAR_DEFAUT } from '../../data/referentiel';

export function OngletCommerciaux({
  version,
  onChange



}: {version: number;onChange: () => void;}) {
  const commerciaux = useAsync(() => getCommerciaux(), [version]);
  const [cible, setCible] = useState<number | null>(null);
  const [telephone, setTelephone] = useState('');
  const [zone, setZone] = useState('');
  const [dsmName, setDsmName] = useState('');
  const [confirmation, setConfirmation] = useState(false);

  return (
    <Section
      titre="Commerciaux"
      description="Coordonnées, zone d'intervention et statut. La désactivation synchronise le compte utilisateur lié.">
      
      <BlocAsync etat={commerciaux} squelette={<Squelette lignes={6} />}>
        {(lignes) => {
          const selectionne = lignes.find((c) => c.id === cible) ?? lignes[0];
          return (
            <div className="space-y-6">
              <div className="flex flex-wrap items-end gap-3">
                <Champ label="Commercial" htmlFor="adm-commercial" className="w-48">
                  <Select
                    id="adm-commercial"
                    value={selectionne?.id ?? ''}
                    onChange={(e) => setCible(Number(e.target.value))}>
                    
                    {lignes.map((c) =>
                    <option key={c.id} value={c.id}>
                        {c.dsmName}
                      </option>
                    )}
                  </Select>
                </Champ>
                <Champ label="Téléphone" htmlFor="adm-tel" className="w-44">
                  <Input
                    id="adm-tel"
                    value={telephone}
                    placeholder={selectionne?.telephone}
                    onChange={(e) => setTelephone(e.target.value)} />
                  
                </Champ>
                <Champ label="Zone" htmlFor="adm-zone" className="w-52">
                  <Input
                    id="adm-zone"
                    value={zone}
                    placeholder={selectionne?.zone}
                    onChange={(e) => setZone(e.target.value)} />
                  
                </Champ>
                <Champ label="DSM name" htmlFor="adm-dsm" className="w-40">
                  <Input
                    id="adm-dsm"
                    value={dsmName}
                    placeholder={selectionne?.dsmName}
                    onChange={(e) => setDsmName(e.target.value)} />
                  
                </Champ>
                <Button
                  variante="primaire"
                  onClick={async () => {
                    if (!selectionne) return;
                    await majCommercial(selectionne.id, {
                      telephone: telephone.trim() || undefined,
                      zone: zone.trim() || undefined,
                      dsmName: dsmName.trim().toUpperCase() || undefined
                    });
                    toast.success('Fiche commerciale mise à jour.');
                    setTelephone('');
                    setZone('');
                    setDsmName('');
                    onChange();
                  }}>
                  
                  Enregistrer
                </Button>
                {selectionne &&
                <Button
                  variante={selectionne.actif ? 'danger' : 'secondaire'}
                  onClick={() => setConfirmation(true)}>
                  
                    {selectionne.actif ? 'Désactiver' : 'Réactiver'}
                  </Button>
                }
              </div>

              <div>
                <TitreBloc>Tous les commerciaux</TitreBloc>
                <DataTable
                  colonnes={[
                  { cle: 'dsmName', entete: 'DSM' },
                  { cle: 'telephone', entete: 'Téléphone' },
                  { cle: 'zone', entete: 'Zone' },
                  {
                    cle: 'alias',
                    entete: 'Alias CSV',
                    rendu: (c) =>
                    c.alias ?
                    <BadgeNeutre ton="accent">{c.alias}</BadgeNeutre> :

                    <span className="text-albarka-muted">Aucun</span>

                  },
                  {
                    cle: 'actif',
                    entete: 'Statut',
                    rendu: (c) =>
                    <BadgeNeutre ton={c.actif ? 'succes' : 'alerte'}>
                          {c.actif ? 'Actif' : 'Désactivé'}
                        </BadgeNeutre>

                  }]
                  }
                  lignes={lignes}
                  cleLigne={(c) => `com-${c.id}`}
                  parPage={12}
                  compact />
                
              </div>

              <ConfirmDialog
                ouvert={confirmation}
                titre={selectionne?.actif ? 'Désactiver ce commercial ?' : 'Réactiver ce commercial ?'}
                message={`${selectionne?.dsmName} et son compte utilisateur suivront le même statut.`}
                libelleConfirmer={selectionne?.actif ? 'Désactiver' : 'Réactiver'}
                onAnnuler={() => setConfirmation(false)}
                onConfirmer={async () => {
                  if (selectionne) {
                    await majCommercial(selectionne.id, { actif: !selectionne.actif });
                    toast.success('Statut mis à jour.');
                    onChange();
                  }
                  setConfirmation(false);
                }} />
              
            </div>);

        }}
      </BlocAsync>
    </Section>);

}

export function OngletAliases({ version, onChange }: {version: number;onChange: () => void;}) {
  const commerciaux = useAsync(() => getCommerciaux(), [version]);
  const [cible, setCible] = useState<number | null>(null);
  const [alias, setAlias] = useState('');

  return (
    <Section
      titre="Aliases CSV"
      description="L'alias identifie le commercial dans les CSV bruts MTN. Sans alias, ni les clients servis ni les appros ne peuvent être extraits.">
      
      <BlocAsync etat={commerciaux} squelette={<Squelette lignes={5} />}>
        {(lignes) => {
          const selectionne = lignes.find((c) => c.id === cible) ?? lignes[0];
          return (
            <div className="space-y-6">
              <div className="flex flex-wrap items-end gap-3">
                <Champ label="Commercial" htmlFor="alias-commercial" className="w-48">
                  <Select
                    id="alias-commercial"
                    value={selectionne?.id ?? ''}
                    onChange={(e) => setCible(Number(e.target.value))}>
                    
                    {lignes.map((c) =>
                    <option key={c.id} value={c.id}>
                        {c.dsmName}
                      </option>
                    )}
                  </Select>
                </Champ>
                <Champ label="Nouvel alias" htmlFor="alias-valeur" className="w-56">
                  <Input
                    id="alias-valeur"
                    value={alias}
                    placeholder={selectionne?.alias ?? 'Laisser vide pour supprimer'}
                    onChange={(e) => setAlias(e.target.value)} />
                  
                </Champ>
                <Button
                  variante="primaire"
                  onClick={async () => {
                    if (!selectionne) return;
                    await majCommercial(selectionne.id, { alias: alias.trim() || null });
                    toast.success(
                      alias.trim() ?
                      `Alias ${alias.trim()} associé à ${selectionne.dsmName}.` :
                      `Alias supprimé pour ${selectionne.dsmName}.`
                    );
                    setAlias('');
                    onChange();
                  }}>
                  
                  Enregistrer
                </Button>
              </div>

              <div className="grid gap-6 xl:grid-cols-2">
                <div>
                  <TitreBloc>Aliases actuels</TitreBloc>
                  <DataTable
                    colonnes={[
                    { cle: 'dsmName', entete: 'Commercial' },
                    {
                      cle: 'alias',
                      entete: 'Alias CSV',
                      rendu: (c) => c.alias ?? '—'
                    }]
                    }
                    lignes={lignes}
                    cleLigne={(c) => `alias-${c.id}`}
                    parPage={12}
                    compact />
                  
                </div>
                <div>
                  <TitreBloc>Aliases de référence</TitreBloc>
                  <DataTable
                    colonnes={[
                    { cle: 'dsmName', entete: 'Commercial' },
                    { cle: 'alias', entete: 'Alias par défaut', rendu: (l) => l.alias ?? '—' }]
                    }
                    lignes={Object.entries(ALIASES_PAR_DEFAUT).map(([dsmName, aliasDefaut]) => ({
                      dsmName,
                      alias: aliasDefaut
                    }))}
                    cleLigne={(l) => `def-${l.dsmName}`}
                    parPage={12}
                    compact />
                  
                </div>
              </div>
            </div>);

        }}
      </BlocAsync>
    </Section>);

}