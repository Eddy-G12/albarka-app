"""
core/appro.py — v2
===================

Suivi des approvisionnements et destockages par commercial.

Source v2 : le classeur Excel généré par la page Transactions
(core/transactions.build_transactions_workbook) — déclenché automatiquement
au dépôt des CSV dans pages/1_Transactions.py via
core/transactions.extract_appro_from_workbook().

Cette logique remplace l'ancien parsing du fichier SUIVI PERFORMANCES CCIAUX DTD.

Règle :
  - TCD - From Name → ligne de l'alias du commercial → APPRO par date
    (le commercial reçoit de l'argent depuis son compte propre = approvisionnement)
  - TCD - To Name   → ligne de l'alias du commercial → DESTOCKAGE par date
    (le commercial envoie de l'argent vers son compte propre = destockage)

Si l'alias n'est pas trouvé dans un onglet pour une date → zéro (pas d'erreur).
Ne s'applique pas aux commerciaux sans alias (FRANCK, PROSPER, CESAIRE tant
qu'ils n'ont pas d'alias configuré).

Les fonctions de lecture/consultation (get_appro, get_appro_par_mois,
get_mois_disponibles_appro) sont conservées à l'identique — la table `appro`
n'a pas changé.
"""

from core.db import get_connection, list_commerciaux


# ---------------------------------------------------------------------------
# Import depuis le classeur Transactions (appelé par pages/1_Transactions.py)
# ---------------------------------------------------------------------------

def import_appro_from_workbook(chemin_workbook, commercial_id: int,
                               alias: str, source_fichier: str) -> dict:
    """
    Extrait et stocke l'appro/destockage depuis un classeur Transactions.

    Délègue l'extraction à core.transactions.extract_appro_from_workbook(),
    puis insère/met à jour la table appro.

    Retourne :
    {
      "nb_lignes_inserees": int,
      "dates_appro":        list[str],
      "dates_destockage":   list[str],
    }
    """
    from core.transactions import extract_appro_from_workbook

    lignes = extract_appro_from_workbook(chemin_workbook, alias)
    if not lignes:
        return {"nb_lignes_inserees": 0, "dates_appro": [], "dates_destockage": []}

    conn = get_connection()
    dates_appro    = []
    dates_destockage = []

    for ligne in lignes:
        conn.execute("""
            INSERT INTO appro
                (commercial_id, date_op, type_op, nb_ops, montant, source_fichier)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(commercial_id, date_op, type_op) DO UPDATE SET
                nb_ops         = excluded.nb_ops,
                montant        = excluded.montant,
                source_fichier = excluded.source_fichier,
                created_at     = datetime('now')
        """, (
            commercial_id,
            ligne["date_op"],
            ligne["type_op"],
            ligne.get("nb_ops", 0),
            ligne.get("montant", 0.0),
            source_fichier,
        ))
        if ligne["type_op"] == "appro":
            dates_appro.append(ligne["date_op"])
        else:
            dates_destockage.append(ligne["date_op"])

    conn.commit()
    conn.close()

    return {
        "nb_lignes_inserees": len(lignes),
        "dates_appro":        dates_appro,
        "dates_destockage":   dates_destockage,
    }


# ---------------------------------------------------------------------------
# Lecture / consultation (inchangé — table appro identique)
# ---------------------------------------------------------------------------

def get_appro(commercial_id: int = None, mois: str = None,
              type_op: str = None) -> list[dict]:
    """
    Liste les opérations appro/destockage avec le nom du commercial.
    Filtrable par commercial_id, mois (AAAA-MM) et/ou type_op.
    """
    conn = get_connection()
    q = """
        SELECT a.*, c.dsm_name
        FROM appro a
        JOIN commerciaux c ON c.id = a.commercial_id
        WHERE 1=1
    """
    params: list = []
    if commercial_id:
        q += " AND a.commercial_id = ?"
        params.append(commercial_id)
    if mois:
        q += " AND strftime('%Y-%m', a.date_op) = ?"
        params.append(mois)
    if type_op:
        q += " AND a.type_op = ?"
        params.append(type_op)
    q += " ORDER BY c.dsm_name, a.date_op"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_appro_par_mois(mois: str = None) -> list[dict]:
    """
    Agrège appro et destockage par commercial × mois.
    Retourne :
    [{dsm_name, mois, nb_appro, montant_appro, nb_destockage, montant_destockage}]
    """
    conn = get_connection()
    q = """
        SELECT
            c.dsm_name,
            strftime('%Y-%m', a.date_op) AS mois,
            SUM(CASE WHEN a.type_op = 'appro'       THEN COALESCE(a.nb_ops,1) ELSE 0 END) AS nb_appro,
            SUM(CASE WHEN a.type_op = 'appro'       THEN a.montant ELSE 0 END) AS montant_appro,
            SUM(CASE WHEN a.type_op = 'destockage'  THEN COALESCE(a.nb_ops,1) ELSE 0 END) AS nb_destockage,
            SUM(CASE WHEN a.type_op = 'destockage'  THEN a.montant ELSE 0 END) AS montant_destockage
        FROM appro a
        JOIN commerciaux c ON c.id = a.commercial_id
        WHERE 1=1
    """
    params: list = []
    if mois:
        q += " AND strftime('%Y-%m', a.date_op) = ?"
        params.append(mois)
    q += " GROUP BY c.dsm_name, strftime('%Y-%m', a.date_op) ORDER BY c.dsm_name, mois"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mois_disponibles_appro() -> list[str]:
    """Retourne la liste des mois (AAAA-MM) pour lesquels des données existent."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT strftime('%Y-%m', date_op) AS mois
        FROM appro
        ORDER BY mois DESC
    """).fetchall()
    conn.close()
    return [r["mois"] for r in rows if r["mois"]]


def get_appro_par_jour(commercial_id: int = None,
                       mois: str = None) -> list[dict]:
    """
    Détail journalier : une ligne par (commercial, date_op, type_op).
    Filtrable par commercial et/ou mois.
    """
    conn = get_connection()
    q = """
        SELECT a.id, a.date_op, a.type_op, a.nb_ops, a.montant,
               a.source_fichier, a.commercial_id, c.dsm_name
        FROM appro a
        JOIN commerciaux c ON c.id = a.commercial_id
        WHERE 1=1
    """
    params: list = []
    if commercial_id:
        q += " AND a.commercial_id = ?"
        params.append(commercial_id)
    if mois:
        q += " AND strftime('%Y-%m', a.date_op) = ?"
        params.append(mois)
    q += " ORDER BY c.dsm_name, a.date_op, a.type_op"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_appro(entry_id: int):
    """Supprime un enregistrement appro/destockage par son id (base uniquement)."""
    conn = get_connection()
    conn.execute("DELETE FROM appro WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
