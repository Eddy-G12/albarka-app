import React, { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { PlusIcon, Trash2Icon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Tabs } from '../components/ui/Tabs';
import { Section, TitreBloc } from '../components/ui/Section';
import { Button } from '../components/ui/Button';
import { Champ, Input, Select } from '../components/ui/Field';
import { DataTable } from '../components/DataTable';
import { MetricCard, GrilleMetriques } from '../components/MetricCard';
import { BarresHorizontales } from '../components/charts/Charts';
import { BlocAsync, Squelette } from '../components/ui/States';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { useAsync } from '../hooks/useAsync';
import {
  enregistrerParrainage,
  getParrainages,
  supprimerParrainage } from
'../services/gestion';
import { PERSONNES_PARRAINAGE } from '../data/gestion';
import { formatNombre, labelDate } from '../utils/format';
import { exporterExcel } from '../utils/export';

export function MomoApp() {
  const [personnes, setPersonnes] = useState<string[]>(PERSONNES_PARRAINAGE);
  const [personne, setPersonne] = useState(PERSONNES_PARRAINAGE[0]);
  const [date, setDate] = useState('2026-08-28');
  const [nb, setNb] = useState('1');
  const [nouvelle, setNouvelle] = useState('');
  const [du, setDu] = useState('2026-08-01');
  const [au, setAu] = useState('2026-08-31');
  const [aSupprimer, setASupprimer] = useState<{personne: string;dateOp: string;} | null>(null);
  const [version, setVersion] = useState(0);

  const periode = useAsync(() => getParrainages(du, au), [du, au, version]);
  const recents = useAsync(() => getParrainages('2026-08-22', '2026-08-31'), [version]);

  const pivot = useMemo(() => {
    const lignes = periode.donnees?.lignes ?? [];
    const dates = [...new Set(lignes.map((l) => l.dateOp))].sort().reverse();
    return dates.map((dateOp) => {
      const entree: Record<string, string | number> = { dateOp };
      personnes.forEach((p) => {
        entree[p] = lignes.find((l) => l.dateOp === dateOp && l.personne === p)?.nb ?? 0;
      });
      return entree;
    });
  }, [periode.donnees, personnes]);

  const saisir = async () => {
    const valeur = Number(nb);
    if (!Number.isFinite(valeur) || valeur <= 0) {
      toast.error('Saisissez un nombre de parrainages supérieur à zéro.');
      return;
    }
    await enregistrerParrainage({ personne, dateOp: date, nb: valeur });
    toast.success(`${valeur} parrainage(s) ajouté(s) pour ${personne} — le cumul est mis à jour.`);
    setNb('1');
    setVersion((v) => v + 1);
  };

  const ongletSaisie =
  <Section
    titre="Saisie des parrainages"
    description="La saisie est cumulative : 3 puis 2 sur la même personne et la même date donnent 5.">
    
      <div className="flex flex-wrap items-end gap-3">
        <Champ label="Personne" htmlFor="personne" className="w-48">
          <Select id="personne" value={personne} onChange={(e) => setPersonne(e.target.value)}>
            {personnes.map((p) =>
          <option key={p} value={p}>
                {p}
              </option>
          )}
          </Select>
        </Champ>
        <Champ label="Date" htmlFor="date-parrainage" className="w-44">
          <Input
          id="date-parrainage"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)} />
        
        </Champ>
        <Champ label="Nb parrainages" htmlFor="nb-parrainage" className="w-36">
          <Input
          id="nb-parrainage"
          type="number"
          min={1}
          value={nb}
          onChange={(e) => setNb(e.target.value)} />
        
        </Champ>
        <Button variante="primaire" icone={<PlusIcon className="h-4 w-4" />} onClick={saisir}>
          Enregistrer
        </Button>
      </div>

      <div className="mt-6">
        <TitreBloc>7 derniers jours</TitreBloc>
        <BlocAsync etat={recents} squelette={<Squelette lignes={5} />}>
          {(donnees) =>
        <DataTable
          colonnes={[
          { cle: 'dateOp', entete: 'Date', rendu: (l) => labelDate(l.dateOp) },
          { cle: 'personne', entete: 'Personne' },
          { cle: 'nb', entete: 'Parrainages', numerique: true }]
          }
          lignes={donnees.lignes}
          cleLigne={(l) => `${l.personne}-${l.dateOp}`}
          parPage={10}
          compact />

        }
        </BlocAsync>
      </div>
    </Section>;


  const ongletDashboard =
  <Section
    titre="Dashboard des parrainages"
    actions={
    <>
          <Champ label="Du" htmlFor="parr-du" className="w-40">
            <Input id="parr-du" type="date" value={du} onChange={(e) => setDu(e.target.value)} />
          </Champ>
          <Champ label="Au" htmlFor="parr-au" className="w-40">
            <Input id="parr-au" type="date" value={au} onChange={(e) => setAu(e.target.value)} />
          </Champ>
        </>
    }>
    
      <BlocAsync etat={periode} squelette={<Squelette lignes={7} />}>
        {(donnees) =>
      <div className="space-y-5">
            <GrilleMetriques colonnes={2}>
              <MetricCard
            libelle="Total réseau sur la période"
            valeur={formatNombre(donnees.total)}
            principale />
          
              <MetricCard
            libelle="Personnes actives"
            valeur={formatNombre(donnees.synthese.filter((s) => s.total > 0).length)} />
          
            </GrilleMetriques>

            <div>
              <TitreBloc>Parrainages par personne</TitreBloc>
              <BarresHorizontales
            donnees={donnees.synthese.map((s) => ({ personne: s.personne, total: s.total }))}
            cleLabel="personne"
            cleValeur="total"
            monetaire={false}
            hauteur={240} />
          
            </div>

            <div>
              <TitreBloc>Pivot jour × personne</TitreBloc>
              <DataTable
            colonnes={[
            { cle: 'dateOp', entete: 'Date', rendu: (l) => labelDate(String(l.dateOp)) },
            ...personnes.map((p) => ({ cle: p, entete: p, numerique: true }))]
            }
            lignes={pivot}
            cleLigne={(l) => String(l.dateOp)}
            parPage={12}
            compact
            onExport={() =>
            exporterExcel('parrainages', [
            {
              nom: 'Synthèse',
              lignes: donnees.synthese.map((s) => ({
                Personne: s.personne,
                Total: s.total
              }))
            },
            {
              nom: 'Détail',
              lignes: donnees.lignes.map((l) => ({
                Date: l.dateOp,
                Personne: l.personne,
                Parrainages: l.nb
              }))
            },
            { nom: 'Pivot', lignes: pivot }]
            )
            } />
          
            </div>
          </div>
      }
      </BlocAsync>
    </Section>;


  const ongletGestion =
  <Section
    titre="Gestion des personnes"
    description="Ajout temporaire pour la session courante et suppression d'un enregistrement précis.">
    
      <div className="flex flex-wrap items-end gap-3">
        <Champ label="Nouvelle personne" htmlFor="nouvelle-personne" className="w-64">
          <Input
          id="nouvelle-personne"
          value={nouvelle}
          onChange={(e) => setNouvelle(e.target.value)}
          placeholder="Prénom" />
        
        </Champ>
        <Button
        icone={<PlusIcon className="h-4 w-4" />}
        onClick={() => {
          const nom = nouvelle.trim();
          if (!nom) return;
          if (personnes.includes(nom)) {
            toast.error('Cette personne est déjà suivie.');
            return;
          }
          setPersonnes((liste) => [...liste, nom]);
          setNouvelle('');
          toast.success(`${nom} ajouté pour cette session.`);
        }}>
        
          Ajouter
        </Button>
      </div>

      <div className="mt-6">
        <TitreBloc>Enregistrements de la période</TitreBloc>
        <BlocAsync etat={periode} squelette={<Squelette lignes={5} />}>
          {(donnees) =>
        <DataTable
          colonnes={[
          { cle: 'dateOp', entete: 'Date', rendu: (l) => labelDate(l.dateOp) },
          { cle: 'personne', entete: 'Personne' },
          { cle: 'nb', entete: 'Parrainages', numerique: true },
          {
            cle: 'actions',
            entete: '',
            triable: false,
            rendu: (l) =>
            <Button
              taille="sm"
              variante="danger"
              icone={<Trash2Icon className="h-3.5 w-3.5" />}
              onClick={() => setASupprimer({ personne: l.personne, dateOp: l.dateOp })}>
              
                      Supprimer
                    </Button>

          }]
          }
          lignes={donnees.lignes}
          cleLigne={(l) => `gest-${l.personne}-${l.dateOp}`}
          recherche
          parPage={12}
          compact />

        }
        </BlocAsync>
      </div>

      <ConfirmDialog
      ouvert={aSupprimer !== null}
      titre="Supprimer cet enregistrement ?"
      message={
      aSupprimer ?
      `Parrainages de ${aSupprimer.personne} du ${labelDate(aSupprimer.dateOp)}.` :
      ''
      }
      onAnnuler={() => setASupprimer(null)}
      onConfirmer={async () => {
        if (aSupprimer) {
          await supprimerParrainage(aSupprimer.personne, aSupprimer.dateOp);
          toast.success('Enregistrement supprimé.');
          setVersion((v) => v + 1);
        }
        setASupprimer(null);
      }} />
    
    </Section>;


  return (
    <div>
      <PageHeader
        titre="MoMo App — Parrainages"
        description="Suivi quotidien des parrainages réalisés par les personnes rattachées au programme." />
      
      <Tabs
        onglets={[
        { id: 'saisie', libelle: 'Saisie', contenu: ongletSaisie },
        { id: 'dashboard', libelle: 'Dashboard', contenu: ongletDashboard },
        { id: 'gestion', libelle: 'Gestion des personnes', contenu: ongletGestion }]
        } />
      
    </div>);

}