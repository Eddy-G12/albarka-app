import React, { useState } from 'react';
import { toast } from 'sonner';
import { UserPlusIcon } from 'lucide-react';
import { Section, TitreBloc } from '../ui/Section';
import { Button } from '../ui/Button';
import { Champ, Input, Select } from '../ui/Field';
import { DataTable } from '../DataTable';
import { BadgeNeutre } from '../StatusBadge';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { BlocAsync, Squelette } from '../ui/States';
import { useAsync } from '../../hooks/useAsync';
import { creerUtilisateur, getUtilisateurs, majUtilisateur } from '../../services/gestion';
import { useAuth } from '../../contexts/AuthContext';
import type { Role } from '../../types';
import { labelDate } from '../../utils/format';

const LIBELLE_ROLE: Record<Role, string> = {
  super_admin: 'Super administrateur',
  admin: 'Administrateur',
  commercial: 'Commercial'
};

export function OngletUtilisateurs({ version, onChange }: {version: number;onChange: () => void;}) {
  const utilisateurs = useAsync(() => getUtilisateurs(), [version]);
  const [username, setUsername] = useState('');
  const [nom, setNom] = useState('');
  const [role, setRole] = useState<Role>('commercial');
  const [dsmName, setDsmName] = useState('');
  const [motDePasse, setMotDePasse] = useState('');

  const creer = async () => {
    if (!username.trim() || !nom.trim() || !motDePasse.trim()) {
      toast.error('Identifiant, nom complet et mot de passe sont requis.');
      return;
    }
    try {
      await creerUtilisateur({
        username: username.trim().toLowerCase(),
        nom: nom.trim(),
        role,
        dsmName: role === 'commercial' ? dsmName.trim().toUpperCase() : undefined
      });
      toast.success('Compte créé.');
      setUsername('');
      setNom('');
      setDsmName('');
      setMotDePasse('');
      onChange();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Création impossible.');
    }
  };

  return (
    <Section
      titre="Comptes utilisateurs"
      description="Chaque rôle détermine la navigation et les actions disponibles après connexion.">
      
      <BlocAsync etat={utilisateurs} squelette={<Squelette lignes={6} />}>
        {(lignes) =>
        <DataTable
          colonnes={[
          { cle: 'username', entete: 'Identifiant' },
          { cle: 'nom', entete: 'Nom complet' },
          { cle: 'role', entete: 'Rôle', rendu: (u) => LIBELLE_ROLE[u.role] },
          { cle: 'dsmName', entete: 'DSM', rendu: (u) => u.dsmName ?? '—' },
          { cle: 'createdAt', entete: 'Créé le', rendu: (u) => labelDate(u.createdAt) },
          {
            cle: 'actif',
            entete: 'Statut',
            rendu: (u) =>
            <BadgeNeutre ton={u.actif ? 'succes' : 'alerte'}>
                    {u.actif ? 'Actif' : 'Désactivé'}
                  </BadgeNeutre>

          }]
          }
          lignes={lignes}
          cleLigne={(u) => `user-${u.id}`}
          recherche
          parPage={12}
          compact />

        }
      </BlocAsync>

      <div className="mt-6 border-t border-albarka-border pt-5">
        <TitreBloc>Créer un compte</TitreBloc>
        <div className="flex flex-wrap items-end gap-3">
          <Champ label="Identifiant" htmlFor="new-username" className="w-44">
            <Input id="new-username" value={username} onChange={(e) => setUsername(e.target.value)} />
          </Champ>
          <Champ label="Nom complet" htmlFor="new-nom" className="w-56">
            <Input id="new-nom" value={nom} onChange={(e) => setNom(e.target.value)} />
          </Champ>
          <Champ label="Rôle" htmlFor="new-role" className="w-48">
            <Select id="new-role" value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="commercial">Commercial</option>
              <option value="admin">Administrateur</option>
              <option value="super_admin">Super administrateur</option>
            </Select>
          </Champ>
          {role === 'commercial' &&
          <Champ label="DSM name" htmlFor="new-dsm" className="w-40">
              <Input id="new-dsm" value={dsmName} onChange={(e) => setDsmName(e.target.value)} />
            </Champ>
          }
          <Champ label="Mot de passe" htmlFor="new-mdp" className="w-44">
            <Input
              id="new-mdp"
              type="password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)} />
            
          </Champ>
          <Button variante="primaire" icone={<UserPlusIcon className="h-4 w-4" />} onClick={creer}>
            Créer le compte
          </Button>
        </div>
      </div>
    </Section>);

}

export function OngletModification({
  version,
  onChange



}: {version: number;onChange: () => void;}) {
  const { utilisateur } = useAuth();
  const utilisateurs = useAsync(() => getUtilisateurs(), [version]);
  const [cible, setCible] = useState<number | null>(null);
  const [nouveauNom, setNouveauNom] = useState('');
  const [nouveauMdp, setNouveauMdp] = useState('');
  const [confirmation, setConfirmation] = useState(false);

  return (
    <Section
      titre="Modifier ou désactiver un compte"
      description="Vous ne pouvez pas modifier votre propre compte depuis cet écran.">
      
      <BlocAsync etat={utilisateurs} squelette={<Squelette lignes={4} />}>
        {(lignes) => {
          const modifiables = lignes.filter((u) => u.id !== utilisateur?.id);
          const selectionne = modifiables.find((u) => u.id === cible) ?? modifiables[0];

          return (
            <div className="space-y-5">
              <div className="flex flex-wrap items-end gap-3">
                <Champ label="Compte" htmlFor="cible" className="w-56">
                  <Select
                    id="cible"
                    value={selectionne?.id ?? ''}
                    onChange={(e) => setCible(Number(e.target.value))}>
                    
                    {modifiables.map((u) =>
                    <option key={u.id} value={u.id}>
                        {u.username} — {u.nom}
                      </option>
                    )}
                  </Select>
                </Champ>
                <Champ label="Nouveau nom" htmlFor="maj-nom" className="w-56">
                  <Input
                    id="maj-nom"
                    value={nouveauNom}
                    placeholder={selectionne?.nom}
                    onChange={(e) => setNouveauNom(e.target.value)} />
                  
                </Champ>
                <Champ label="Nouveau mot de passe" htmlFor="maj-mdp" className="w-52">
                  <Input
                    id="maj-mdp"
                    type="password"
                    value={nouveauMdp}
                    onChange={(e) => setNouveauMdp(e.target.value)} />
                  
                </Champ>
                <Button
                  variante="primaire"
                  onClick={async () => {
                    if (!selectionne) return;
                    if (!nouveauNom.trim() && !nouveauMdp.trim()) {
                      toast.error('Renseignez au moins un champ à modifier.');
                      return;
                    }
                    await majUtilisateur(selectionne.id, {
                      nom: nouveauNom.trim() || undefined
                    });
                    toast.success('Compte mis à jour.');
                    setNouveauNom('');
                    setNouveauMdp('');
                    onChange();
                  }}>
                  
                  Enregistrer
                </Button>
              </div>

              {selectionne &&
              <div className="flex flex-wrap items-center gap-3 rounded-md border border-albarka-border bg-albarka-bg px-4 py-3">
                  <p className="text-xs text-albarka-muted">
                    {selectionne.username} est actuellement{' '}
                    <strong>{selectionne.actif ? 'actif' : 'désactivé'}</strong>.
                  </p>
                  <Button
                  variante={selectionne.actif ? 'danger' : 'secondaire'}
                  taille="sm"
                  onClick={() => setConfirmation(true)}>
                  
                    {selectionne.actif ? 'Désactiver le compte' : 'Réactiver le compte'}
                  </Button>
                </div>
              }

              <ConfirmDialog
                ouvert={confirmation}
                titre={selectionne?.actif ? 'Désactiver ce compte ?' : 'Réactiver ce compte ?'}
                message={
                selectionne?.actif ?
                `${selectionne?.username} ne pourra plus se connecter tant que le compte reste désactivé.` :
                `${selectionne?.username} pourra de nouveau se connecter.`
                }
                note="Le commercial rattaché suit automatiquement le même statut."
                libelleConfirmer={selectionne?.actif ? 'Désactiver' : 'Réactiver'}
                onAnnuler={() => setConfirmation(false)}
                onConfirmer={async () => {
                  if (selectionne) {
                    await majUtilisateur(selectionne.id, { actif: !selectionne.actif });
                    toast.success('Statut du compte mis à jour.');
                    onChange();
                  }
                  setConfirmation(false);
                }} />
              
            </div>);

        }}
      </BlocAsync>
    </Section>);

}