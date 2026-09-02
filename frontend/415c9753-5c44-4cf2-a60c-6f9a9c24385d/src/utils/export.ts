import * as XLSX from 'xlsx';

export interface FeuilleExport {
  nom: string;
  lignes: Record<string, string | number | null>[];
}

/**
 * Génération du classeur côté navigateur pendant la phase maquette.
 * Au branchement FastAPI, ces boutons appelleront l'API et récupéreront
 * le binaire produit par openpyxl (header #1F4E78, lignes alternées, Arial 10).
 */
export function exporterExcel(nomFichier: string, feuilles: FeuilleExport[]): void {
  const classeur = XLSX.utils.book_new();
  feuilles.forEach((feuille) => {
    const donnees = feuille.lignes.length ? feuille.lignes : [{ Information: 'Aucune donnée' }];
    const ws = XLSX.utils.json_to_sheet(donnees);
    const colonnes = Object.keys(donnees[0]);
    ws['!cols'] = colonnes.map((col) => ({
      wch: Math.min(
        38,
        Math.max(
          col.length + 2,
          ...donnees.map((l) => String(l[col] ?? '').length + 2)
        )
      )
    }));
    ws['!freeze'] = { xSplit: 0, ySplit: 1 };
    XLSX.utils.book_append_sheet(classeur, ws, feuille.nom.slice(0, 31));
  });
  XLSX.writeFile(classeur, `${nomFichier}.xlsx`);
}