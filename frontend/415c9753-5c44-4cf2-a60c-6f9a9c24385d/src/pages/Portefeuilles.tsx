import React, { useState } from 'react';
import { toast } from 'sonner';
import { ChevronDownIcon, Trash2Icon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Tabs } from '../components/ui/Tabs';
import { Section, TitreBloc } from '../components/ui/Section';
import { FileDropzone } from '../components/FileDropzone';
import { DataTable } from '../components/DataTable';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { Button } from '../components/ui/Button';
import { Champ, Input, Select } from '../components/ui/Field';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { BadgeNeutre } from '../components/StatusBadge';
import { BlocAsync, EtatVide, Squelette } from '../components/ui/States';
import { useAuth } from '../contexts/AuthContext';
import { useAsync } from '../hooks/useAsync';
import { getClientsPortefeuille, getCouverturePortefeuille, getPortefeuilles } from '../services/terrain';
import { store } from '../services/store';
import { formatNombre, formatPourcent, labelDate } from '../utils/format';
import { exporterExcel } from '../utils/export';

function OngletImport() {
  const [commercialId, setCommercialId] = useState(String(store.commerciaux[0]?.id ?? ''));
  const [nom, setNom] = useState('');

  return (
    <Section
      titre="Import d'un portefeuille"
      description="Fichier Excel ALBARKA : l'en-tête est détecté automatiquement, quel que soit le nombre de lignes vides en haut.">
      
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Champ label="Commercial" htmlFor="pf-commercial" className="w-52">
          <Select
            id="pf-commercial"
            value={commercialId}
            onChange={(e) => setCommercialId(e.target.value)}>
            
            {store.commerciaux.map((c) =>
            <option key={c.id} value={c.id}>
                {c.dsmName}
              </option>
            )}
          </Select>
        </Champ>
        <Champ label="Nom du portefeuille" htmlFor="pf-nom" className="w-64">
          <Input
            id="pf-nom"
            value={nom}
            onChange={(e) => setNom(e.target.value)}
            placeholder="Portefeuille EWANE Q4" />
          
        </Champ>
      </div>

      <FileDropzone
        accept=".xlsx"
        multiple={false}
        legende="Colonnes attendues : Nom du client, numéro_ccial (MSISDN 237XXXXXXXXX), pos_profile."
        onTermine={() => toast.success('Aperçu des 10 premiers clients prêt — confirmez pour enregistrer.')} />
      

      <p className="mt-3 text-xs text-albarka-muted">
        Après lecture, les 10 premiers clients sont affichés pour vérification avant enregistrement
        dans les tables portefeuilles et clients.
      </p>
    </Section>);

}

function LignePortefeuille({
  portefeuille,
  peutSupprimer,
  onSupprimer




}: {portefeuille: {id: number;nom: string;dsmName: string;dateImport: string;nbClients: number;};peutSupprimer: boolean;onSupprimer: () => void;}) {
  const [ouvert, setOuvert] = useState(false);
  const clients = useAsync(
    () => ouvert ? getClientsPortefeuille(portefeuille.id) : Promise.resolve([]),
    [ouvert, portefeuille.id]
  );

  return (
    <li className="rounded-md border border-albarka-border bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <p className="text-sm font-semibold text-albarka-black">{portefeuille.nom}</p>
          <p className="mt-0.5 flex flex-wrap items-center gap-2 text-2xs text-albarka-muted">
            <BadgeNeutre>{portefeuille.dsmName}</BadgeNeutre>
            <span className="num">{formatNombre(portefeuille.nbClients)} clients</span>
            <span>importé le {labelDate(portefeuille.dateImport)}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button taille="sm" onClick={() => setOuvert((v) => !v)}>
            {ouvert ? 'Masquer' : 'Voir les clients'}
            <ChevronDownIcon
              className={`h-3.5 w-3.5 transition-transform duration-150 ease-out ${ouvert ? 'rotate-180' : ''}`}
              aria-hidden />
            
          </Button>
          {peutSupprimer &&
          <Button
            taille="sm"
            variante="danger"
            icone={<Trash2Icon className="h-3.5 w-3.5" />}
            onClick={onSupprimer}>
            
              Supprimer
            </Button>
          }
        </div>
      </div>
      {ouvert &&
      <div className="border-t border-albarka-border px-4 py-4">
          <BlocAsync etat={clients} squelette={<Squelette lignes={5} />}>
            {(lignes) =>
          <DataTable
            colonnes={[
            { cle: 'nom', entete: 'Client' },
            { cle: 'telephone', entete: 'MSISDN' },
            { cle: 'localite', entete: 'Profil POS' }]
            }
            lignes={lignes}
            cleLigne={(c) => `client-pf-${c.id}`}
            recherche
            parPage={10}
            compact />

          }
          </BlocAsync>
        </div>
      }
    </li>);

}

function OngletConsultation() {
  const { peutSupprimer } = useAuth();
  const [commercialId, setCommercialId] = useState<'tous' | number>('tous');
  const [aSupprimer, setASupprimer] = useState<number | null>(null);
  const portefeuilles = useAsync(
    () => getPortefeuilles(commercialId === 'tous' ? undefined : commercialId),
    [commercialId]
  );

  return (
    <Section
      titre="Portefeuilles enregistrés"
      actions={
      <Champ label="Commercial" htmlFor="filtre-pf" className="w-52">
          <Select
          id="filtre-pf"
          value={String(commercialId)}
          onChange={(e) =>
          setCommercialId(e.target.value === 'tous' ? 'tous' : Number(e.target.value))
          }>
          
            <option value="tous">Tous les commerciaux</option>
            {store.commerciaux.map((c) =>
          <option key={c.id} value={c.id}>
                {c.dsmName}
              </option>
          )}
          </Select>
        </Champ>
      }>
      
      <BlocAsync etat={portefeuilles} squelette={<Squelette lignes={4} hauteur="h-12" />}>
        {(lignes) =>
        lignes.length === 0 ?
        <EtatVide
          titre="Aucun portefeuille"
          message="Aucun portefeuille n'a encore été importé pour ce commercial." /> :


        <ul className="space-y-2">
              {lignes.map((pf) =>
          <LignePortefeuille
            key={pf.id}
            portefeuille={pf}
            peutSupprimer={peutSupprimer}
            onSupprimer={() => setASupprimer(pf.id)} />

          )}
            </ul>

        }
      </BlocAsync>

      <ConfirmDialog
        ouvert={aSupprimer !== null}
        titre="Supprimer ce portefeuille ?"
        message="Le portefeuille et ses clients seront retirés de la base."
        note="Aucun fichier Excel n'est supprimé sur le disque."
        onAnnuler={() => setASupprimer(null)}
        onConfirmer={() => {
          setASupprimer(null);
          toast.success('Portefeuille supprimé de la base.');
          portefeuilles.recharger();
        }} />
      
    </Section>);

}

function OngletCouverture() {
  const [portefeuilleId, setPortefeuilleId] = useState(1);
  const [affichage, setAffichage] = useState<'tous' | 'touches' | 'non_touches'>('tous');
  const [fichiers, setFichiers] = useState<File[]>([]);
  const [couverture, setCouverture] = useState<Awaited<ReturnType<typeof getCouverturePortefeuille>> | null>(null);
  const [chargement, setChargement] = useState(false);
  const listePortefeuilles = useAsync(() => getPortefeuilles(), []);

  const calculer = async () => {
    if (fichiers.length === 0) return;
    setChargement(true);
    try {
      const result = await getCouverturePortefeuille(portefeuilleId, fichiers);
      setCouverture(result);
    } finally {
      setChargement(false);
    }
  };

  return (
    <div className="space-y-6">
      <Section
        titre="Rapprochement portefeuille × transactions"
        description="Le rapprochement se fait par MSISDN, extrait des colonnes From / To des CSV bruts (FRI:237XXXXXXXXX/MSISDN)."
        actions={
        <>
            <Champ label="Portefeuille" htmlFor="couv-pf" className="w-64">
              <Select
              id="couv-pf"
              value={portefeuilleId}
              onChange={(e) => setPortefeuilleId(Number(e.target.value))}>
              
                {(listePortefeuilles.donnees ?? []).map((pf) =>
              <option key={pf.id} value={pf.id}>
                    {pf.nom}
                  </option>
              )}
              </Select>
            </Champ>
            <Champ label="Affichage" htmlFor="couv-filtre" className="w-44">
              <Select
              id="couv-filtre"
              value={affichage}
              onChange={(e) => setAffichage(e.target.value as typeof affichage)}>
              
                <option value="tous">Tous les clients</option>
                <option value="touches">Clients touchés</option>
                <option value="non_touches">Clients non touchés</option>
              </Select>
            </Champ>
          </>
        }>
        
        <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-400 transition-colors bg-gray-50">
          <span className="text-sm text-gray-500">
            {fichiers.length > 0
              ? `${fichiers.length} fichier(s) sélectionné(s)`
              : 'Cliquez pour déposer des CSV bruts MTN'}
          </span>
          <input
            type="file"
            accept=".csv"
            multiple
            className="hidden"
            onChange={(e) => setFichiers(Array.from(e.target.files ?? []))}
          />
        </label>

        <Button
          onClick={calculer}
          disabled={fichiers.length === 0 || chargement}>
          {chargement ? 'Calcul en cours…' : 'Calculer la couverture'}
        </Button>
      </Section>

      <Section titre="Résultat de la couverture">
        {couverture === null ? (
          <p className="text-sm text-gray-500">Aucun calcul effectué. Déposez des CSV puis cliquez sur « Calculer ».</p>
        ) : (() => {
          const donnees = couverture;
          const lignes = donnees.lignes.filter((l) =>
            affichage === 'touches' ? l.nbContacts > 0 :
            affichage === 'non_touches' ? l.nbContacts === 0 : true
          );
          return (
            <div className="space-y-5">
              <GrilleMetriques colonnes={4}>
                  <MetricCard
                    libelle="Taux de couverture"
                    valeur={formatPourcent(donnees.tauxCouverture)}
                    principale />
                  
                  <MetricCard libelle="Clients touchés" valeur={formatNombre(donnees.clientsTouches)} />
                  <MetricCard
                    libelle="Clients non touchés"
                    valeur={formatNombre(donnees.clientsNonTouches)} />
                  
                  <MetricCard libelle="Total contacts" valeur={formatNombre(donnees.totalContacts)} />
                </GrilleMetriques>

                <div>
                  <TitreBloc>Détail par client</TitreBloc>
                  <DataTable
                    colonnes={[
                    { cle: 'msisdn', entete: 'MSISDN' },
                    { cle: 'nom', entete: 'Nom associé' },
                    { cle: 'profilPos', entete: 'Profil POS' },
                    { cle: 'nbContacts', entete: 'Nb contacts', numerique: true },
                    {
                      cle: 'premiere',
                      entete: 'Première transaction',
                      rendu: (l) => l.premiere ? labelDate(l.premiere) : '—'
                    },
                    {
                      cle: 'derniere',
                      entete: 'Dernière transaction',
                      rendu: (l) => l.derniere ? labelDate(l.derniere) : '—'
                    }]
                    }
                    lignes={lignes}
                    cleLigne={(l) => `couv-${l.msisdn}`}
                    recherche
                    parPage={15}
                    compact
                    onExport={() =>
                    exporterExcel(`couverture-portefeuille-${portefeuilleId}`, [
                    {
                      nom: 'Suivi contacts',
                      lignes: donnees.lignes.map((l) => ({
                        MSISDN: l.msisdn,
                        'Nom associé': l.nom,
                        'Profil POS': l.profilPos,
                        'Nombre de contacts': l.nbContacts,
                        'Première transaction': l.premiere ?? '',
                        'Dernière transaction': l.derniere ?? ''
                      }))
                    }]
                    )
                    } />
                  
                </div>
              </div>
          );
        })()}
      </Section>
    </div>);

}

export function Portefeuilles() {
  const { peutDeposer } = useAuth();

  return (
    <div>
      <PageHeader
        titre="Portefeuilles"
        description="Listes clients par commercial et mesure de la couverture terrain à partir des transactions réelles." />
      
      <Tabs
        onglets={[
        ...(peutDeposer ? [{ id: 'import', libelle: 'Import', contenu: <OngletImport /> }] : []),
        { id: 'consultation', libelle: 'Consultation', contenu: <OngletConsultation /> },
        { id: 'couverture', libelle: 'Couverture', contenu: <OngletCouverture /> }]
        } />
      
    </div>);

}