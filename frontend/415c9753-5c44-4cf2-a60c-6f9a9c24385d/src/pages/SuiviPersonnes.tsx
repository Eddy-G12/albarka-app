import React, { useState } from 'react';
import { toast } from 'sonner';
import { PlusIcon, Trash2Icon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Tabs } from '../components/ui/Tabs';
import { Section, TitreBloc } from '../components/ui/Section';
import { Button } from '../components/ui/Button';
import { Champ, Input, Select } from '../components/ui/Field';
import { DataTable } from '../components/DataTable';
import { GrilleMetriques, MetricCard } from '../components/MetricCard';
import { BlocAsync, Squelette } from '../components/ui/States';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { useAsync } from '../hooks/useAsync';
import { enregistrerSuivi, getSuiviPersonnes, supprimerSuivi } from '../services/gestion';
import { COMMERCIAUX_SUIVIS } from '../data/gestion';
import { store } from '../services/store';
import { formatFcfa, formatNombre, labelDateHeure } from '../utils/format';
import { exporterExcel } from '../utils/export';

const COMMERCIAUX_CONCERNES = () =>
store.commerciaux.filter((c) => COMMERCIAUX_SUIVIS.includes(c.dsmName));

export function SuiviPersonnes() {
  const concernes = COMMERCIAUX_CONCERNES();
  const [commercialId, setCommercialId] = useState(concernes[0]?.id ?? 1);
  const [nomPersonne, setNomPersonne] = useState('');
  const [montant, setMontant] = useState('');
  const [date, setDate] = useState('2026-08-28');
  const [heure, setHeure] = useState('10:30');
  const [filtreCommercial, setFiltreCommercial] = useState<'tous' | number>('tous');
  const [du, setDu] = useState('2026-08-01');
  const [au, setAu] = useState('2026-08-31');
  const [aSupprimer, setASupprimer] = useState<number | null>(null);
  const [version, setVersion] = useState(0);

  const donneesFiltrees = useAsync(
    () =>
    getSuiviPersonnes({
      commercialId: filtreCommercial === 'tous' ? undefined : filtreCommercial,
      du,
      au
    }),
    [filtreCommercial, du, au, version]
  );
  const recentes = useAsync(() => getSuiviPersonnes({}), [version]);

  const saisir = async () => {
    const valeur = Number(montant);
    if (!nomPersonne.trim() || !Number.isFinite(valeur) || valeur <= 0) {
      toast.error('Renseignez la personne suivie et un montant valide.');
      return;
    }
    await enregistrerSuivi({
      commercialId,
      nomPersonne: nomPersonne.trim(),
      montant: valeur,
      dateHeure: `${date} ${heure}:00`
    });
    toast.success('Entrée enregistrée.');
    setNomPersonne('');
    setMontant('');
    setVersion((v) => v + 1);
  };

  const ongletSaisie =
  <Section
    titre="Nouvelle entrée"
    description="Réservé aux commerciaux concernés : CESAIRE, ANTOINE, PARFAIT, ERVE, STEPHANE.">
    
      <div className="flex flex-wrap items-end gap-3">
        <Champ label="Commercial" htmlFor="sp-commercial" className="w-48">
          <Select
          id="sp-commercial"
          value={commercialId}
          onChange={(e) => setCommercialId(Number(e.target.value))}>
          
            {concernes.map((c) =>
          <option key={c.id} value={c.id}>
                {c.dsmName}
              </option>
          )}
          </Select>
        </Champ>
        <Champ label="Personne suivie" htmlFor="sp-personne" className="w-56">
          <Input
          id="sp-personne"
          value={nomPersonne}
          onChange={(e) => setNomPersonne(e.target.value)}
          placeholder="Mme Ngo Bell" />
        
        </Champ>
        <Champ label="Montant (FCFA)" htmlFor="sp-montant" className="w-40">
          <Input
          id="sp-montant"
          type="number"
          min={0}
          value={montant}
          onChange={(e) => setMontant(e.target.value)} />
        
        </Champ>
        <Champ label="Date" htmlFor="sp-date" className="w-40">
          <Input id="sp-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </Champ>
        <Champ label="Heure" htmlFor="sp-heure" className="w-32">
          <Input id="sp-heure" type="time" value={heure} onChange={(e) => setHeure(e.target.value)} />
        </Champ>
        <Button variante="primaire" icone={<PlusIcon className="h-4 w-4" />} onClick={saisir}>
          Enregistrer
        </Button>
      </div>

      <div className="mt-6">
        <TitreBloc>20 dernières entrées</TitreBloc>
        <BlocAsync etat={recentes} squelette={<Squelette lignes={6} />}>
          {(donnees) =>
        <DataTable
          colonnes={[
          { cle: 'dateHeure', entete: 'Date et heure', rendu: (l) => labelDateHeure(l.dateHeure) },
          { cle: 'dsmName', entete: 'Commercial' },
          { cle: 'nomPersonne', entete: 'Personne suivie' },
          {
            cle: 'montant',
            entete: 'Montant',
            numerique: true,
            rendu: (l) => formatFcfa(l.montant)
          }]
          }
          lignes={donnees.lignes.slice(0, 20)}
          cleLigne={(l) => `recent-${l.id}`}
          parPage={10}
          compact />

        }
        </BlocAsync>
      </div>
    </Section>;


  const filtres =
  <>
      <Champ label="Commercial" htmlFor="sp-filtre" className="w-48">
        <Select
        id="sp-filtre"
        value={String(filtreCommercial)}
        onChange={(e) =>
        setFiltreCommercial(e.target.value === 'tous' ? 'tous' : Number(e.target.value))
        }>
        
          <option value="tous">Tous</option>
          {concernes.map((c) =>
        <option key={c.id} value={c.id}>
              {c.dsmName}
            </option>
        )}
        </Select>
      </Champ>
      <Champ label="Du" htmlFor="sp-du" className="w-40">
        <Input id="sp-du" type="date" value={du} onChange={(e) => setDu(e.target.value)} />
      </Champ>
      <Champ label="Au" htmlFor="sp-au" className="w-40">
        <Input id="sp-au" type="date" value={au} onChange={(e) => setAu(e.target.value)} />
      </Champ>
    </>;


  const ongletDashboard =
  <Section titre="Synthèse des montants suivis" actions={filtres}>
      <BlocAsync etat={donneesFiltrees} squelette={<Squelette lignes={7} />}>
        {(donnees) =>
      <div className="space-y-5">
            <GrilleMetriques colonnes={3}>
              <MetricCard
            libelle="Montant total"
            valeur={formatFcfa(donnees.montantTotal, true)}
            unite="FCFA"
            principale />
          
              <MetricCard
            libelle="Personnes distinctes"
            valeur={formatNombre(donnees.personnesDistinctes)} />
          
              <MetricCard libelle="Entrées" valeur={formatNombre(donnees.lignes.length)} />
            </GrilleMetriques>

            <div>
              <TitreBloc>Par commercial et personne suivie</TitreBloc>
              <DataTable
            colonnes={[
            { cle: 'dsmName', entete: 'Commercial' },
            { cle: 'nomPersonne', entete: 'Personne suivie' },
            {
              cle: 'montant',
              entete: 'Montant cumulé',
              numerique: true,
              rendu: (l) => formatFcfa(l.montant)
            },
            { cle: 'nbEntrees', entete: 'Nb entrées', numerique: true }]
            }
            lignes={donnees.synthese}
            cleLigne={(l) => `syn-${l.dsmName}-${l.nomPersonne}`}
            recherche
            parPage={12}
            compact />
          
            </div>

            <div>
              <TitreBloc>Historique chronologique</TitreBloc>
              <DataTable
            colonnes={[
            {
              cle: 'dateHeure',
              entete: 'Date et heure',
              rendu: (l) => labelDateHeure(l.dateHeure)
            },
            { cle: 'dsmName', entete: 'Commercial' },
            { cle: 'nomPersonne', entete: 'Personne suivie' },
            {
              cle: 'montant',
              entete: 'Montant',
              numerique: true,
              rendu: (l) => formatFcfa(l.montant)
            }]
            }
            lignes={donnees.lignes}
            cleLigne={(l) => `hist-${l.id}`}
            parPage={15}
            compact
            onExport={() =>
            exporterExcel('suivi-personnes', [
            {
              nom: 'Synthèse',
              lignes: donnees.synthese.map((l) => ({
                Commercial: l.dsmName,
                'Personne suivie': l.nomPersonne,
                'Montant cumulé': l.montant,
                'Nb entrées': l.nbEntrees
              }))
            },
            {
              nom: 'Historique',
              lignes: donnees.lignes.map((l) => ({
                'Date et heure': l.dateHeure,
                Commercial: l.dsmName,
                'Personne suivie': l.nomPersonne,
                Montant: l.montant
              }))
            }]
            )
            } />
          
            </div>
          </div>
      }
      </BlocAsync>
    </Section>;


  const ongletGestion =
  <Section
    titre="Suppression d'entrées"
    description="Filtrez par commercial et par période, puis supprimez l'entrée concernée."
    actions={filtres}>
    
      <BlocAsync etat={donneesFiltrees} squelette={<Squelette lignes={6} />}>
        {(donnees) =>
      <DataTable
        colonnes={[
        { cle: 'dateHeure', entete: 'Date et heure', rendu: (l) => labelDateHeure(l.dateHeure) },
        { cle: 'dsmName', entete: 'Commercial' },
        { cle: 'nomPersonne', entete: 'Personne suivie' },
        {
          cle: 'montant',
          entete: 'Montant',
          numerique: true,
          rendu: (l) => formatFcfa(l.montant)
        },
        {
          cle: 'actions',
          entete: '',
          triable: false,
          rendu: (l) =>
          <Button
            taille="sm"
            variante="danger"
            icone={<Trash2Icon className="h-3.5 w-3.5" />}
            onClick={() => setASupprimer(l.id)}>
            
                    Supprimer
                  </Button>

        }]
        }
        lignes={donnees.lignes}
        cleLigne={(l) => `gest-sp-${l.id}`}
        recherche
        parPage={15}
        compact />

      }
      </BlocAsync>

      <ConfirmDialog
      ouvert={aSupprimer !== null}
      titre="Supprimer cette entrée ?"
      message="L'entrée sera retirée de la base de suivi."
      onAnnuler={() => setASupprimer(null)}
      onConfirmer={async () => {
        if (aSupprimer !== null) {
          await supprimerSuivi(aSupprimer);
          toast.success('Entrée supprimée.');
          setVersion((v) => v + 1);
        }
        setASupprimer(null);
      }} />
    
    </Section>;


  return (
    <div>
      <PageHeader
        titre="Suivi Personnes Spécialement Suivies"
        description="Montants suivis dans le temps, par commercial et par personne accompagnée." />
      
      <Tabs
        onglets={[
        { id: 'saisie', libelle: 'Saisie', contenu: ongletSaisie },
        { id: 'dashboard', libelle: 'Dashboard', contenu: ongletDashboard },
        { id: 'gestion', libelle: 'Gestion', contenu: ongletGestion }]
        } />
      
    </div>);

}