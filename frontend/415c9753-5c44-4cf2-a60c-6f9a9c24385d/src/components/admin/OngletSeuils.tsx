import React, { useState } from 'react';
import { toast } from 'sonner';
import { Section, TitreBloc } from '../ui/Section';
import { Button } from '../ui/Button';
import { Champ, Input } from '../ui/Field';
import { DataTable } from '../DataTable';
import { GrilleMetriques, MetricCard } from '../MetricCard';
import { BlocAsync, Squelette } from '../ui/States';
import { useAsync } from '../../hooks/useAsync';
import { enregistrerSeuil, getSeuils } from '../../services/gestion';
import { useAuth } from '../../contexts/AuthContext';
import { seuilCourant } from '../../services/cash';
import { MOIS_COURANT } from '../../data/seed';
import { formatFcfa, labelDate, labelMois } from '../../utils/format';

export function OngletSeuils({ version, onChange }: {version: number;onChange: () => void;}) {
  const { utilisateur } = useAuth();
  const seuils = useAsync(() => getSeuils(), [version]);
  const [seuilIn, setSeuilIn] = useState('');
  const [seuilOut, setSeuilOut] = useState('');
  const [mois, setMois] = useState('');

  const enregistrer = async () => {
    const valeurIn = Number(seuilIn);
    const valeurOut = Number(seuilOut);
    if (!seuilIn && !seuilOut) {
      toast.error('Renseignez au moins un seuil.');
      return;
    }
    const cible = mois.trim() || null;
    if (seuilIn) {
      await enregistrerSeuil({
        typeFlux: 'cash_in',
        valeur: valeurIn,
        mois: cible,
        createdBy: utilisateur?.username ?? 'inconnu'
      });
    }
    if (seuilOut) {
      await enregistrerSeuil({
        typeFlux: 'cash_out',
        valeur: valeurOut,
        mois: cible,
        createdBy: utilisateur?.username ?? 'inconnu'
      });
    }
    toast.success(cible ? `Seuils enregistrés pour ${labelMois(cible)}.` : 'Seuils globaux mis à jour.');
    setSeuilIn('');
    setSeuilOut('');
    setMois('');
    onChange();
  };

  return (
    <Section
      titre="Seuils cash in / cash out"
      description="Un seuil mensuel prend le pas sur le seuil global pour le mois concerné.">
      
      <div className="space-y-6">
        <GrilleMetriques colonnes={2}>
          <MetricCard
            libelle={`Seuil cash in appliqué (${labelMois(MOIS_COURANT)})`}
            valeur={formatFcfa(seuilCourant('cash_in', MOIS_COURANT))}
            unite="FCFA"
            principale />
          
          <MetricCard
            libelle={`Seuil cash out appliqué (${labelMois(MOIS_COURANT)})`}
            valeur={formatFcfa(seuilCourant('cash_out', MOIS_COURANT))}
            unite="FCFA" />
          
        </GrilleMetriques>

        <div className="flex flex-wrap items-end gap-3 border-t border-albarka-border pt-5">
          <Champ label="Seuil cash in" htmlFor="seuil-in" className="w-44">
            <Input
              id="seuil-in"
              type="number"
              min={0}
              value={seuilIn}
              onChange={(e) => setSeuilIn(e.target.value)} />
            
          </Champ>
          <Champ label="Seuil cash out" htmlFor="seuil-out" className="w-44">
            <Input
              id="seuil-out"
              type="number"
              min={0}
              value={seuilOut}
              onChange={(e) => setSeuilOut(e.target.value)} />
            
          </Champ>
          <Champ label="Mois (optionnel)" htmlFor="seuil-mois" className="w-44">
            <Input
              id="seuil-mois"
              value={mois}
              placeholder="AAAA-MM"
              onChange={(e) => setMois(e.target.value)} />
            
          </Champ>
          <Button variante="primaire" onClick={enregistrer}>
            Enregistrer
          </Button>
        </div>

        <div>
          <TitreBloc>Historique des seuils</TitreBloc>
          <BlocAsync etat={seuils} squelette={<Squelette lignes={4} />}>
            {(lignes) =>
            <DataTable
              colonnes={[
              {
                cle: 'typeFlux',
                entete: 'Flux',
                rendu: (s) => s.typeFlux === 'cash_in' ? 'Cash In' : 'Cash Out'
              },
              {
                cle: 'valeur',
                entete: 'Valeur',
                numerique: true,
                rendu: (s) => formatFcfa(s.valeur)
              },
              {
                cle: 'mois',
                entete: 'Portée',
                rendu: (s) => s.mois ? labelMois(s.mois) : 'Seuil global'
              },
              { cle: 'createdBy', entete: 'Défini par' },
              { cle: 'createdAt', entete: 'Le', rendu: (s) => labelDate(s.createdAt) }]
              }
              lignes={lignes}
              cleLigne={(s) => `seuil-${s.id}`}
              parPage={10}
              compact />

            }
          </BlocAsync>
        </div>
      </div>
    </Section>);

}