import React, { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Tabs } from '../components/ui/Tabs';
import {
  OngletModification,
  OngletUtilisateurs } from
'../components/admin/OngletUtilisateurs';
import { OngletAliases, OngletCommerciaux } from '../components/admin/OngletCommerciaux';
import { OngletSeuils } from '../components/admin/OngletSeuils';

export function Administration() {
  const [version, setVersion] = useState(0);
  const rafraichir = () => setVersion((v) => v + 1);

  return (
    <div>
      <PageHeader
        titre="Administration"
        description="Comptes, fiches commerciales, aliases CSV et seuils d'alerte du réseau." />
      
      <Tabs
        onglets={[
        {
          id: 'utilisateurs',
          libelle: 'Utilisateurs',
          contenu: <OngletUtilisateurs version={version} onChange={rafraichir} />
        },
        {
          id: 'modification',
          libelle: 'Modifier / Désactiver',
          contenu: <OngletModification version={version} onChange={rafraichir} />
        },
        {
          id: 'commerciaux',
          libelle: 'Commerciaux',
          contenu: <OngletCommerciaux version={version} onChange={rafraichir} />
        },
        {
          id: 'aliases',
          libelle: 'Aliases CSV',
          contenu: <OngletAliases version={version} onChange={rafraichir} />
        },
        {
          id: 'seuils',
          libelle: 'Seuils',
          contenu: <OngletSeuils version={version} onChange={rafraichir} />
        }]
        } />
      
    </div>);

}