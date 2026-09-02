import React, { useEffect, useState } from 'react';
import { DownloadIcon } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { SelecteurDateQr } from '../components/Filtres';
import { Button } from '../components/ui/Button';
import { SectionQr } from '../components/dashboard/SectionQr';
import { useFiltres } from '../contexts/FiltresContext';
import { getDatesQr } from '../services/qr';
import { labelDate } from '../utils/format';

export function DashboardQr() {
  const { dateQr, setDateQr } = useFiltres();
  const [datesDisponibles, setDatesDisponibles] = useState<string[]>([]);

  useEffect(() => {
    getDatesQr().then(setDatesDisponibles).catch(() => {});
  }, []);

  return (
    <div>
      <PageHeader
        titre="Dashboard QR Code"
        description={`Photographie du réseau d'agents au ${labelDate(dateQr)}, par statut, segment et DSM.`}
        filtres={
          <SelecteurDateQr
            valeur={dateQr}
            onChange={setDateQr}
            dates={datesDisponibles.length > 0 ? datesDisponibles : undefined}
          />
        }
        actions={
          <Button icone={<DownloadIcon className="h-4 w-4" />} onClick={() => {}}>
            Exporter le rapport
          </Button>
        } />

      <SectionQr dateRef={dateQr} />
    </div>);

}