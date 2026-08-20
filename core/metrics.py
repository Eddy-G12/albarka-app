"""
core/metrics.py
================

Calcul des indicateurs de réactivité commerciale à partir des listings
Mobile Money. Ce module est utilisé par core/cashflow.py et peut être
appelé directement pour des analyses ad hoc.

Fonctions exportées :
  - load_transactions_full(source)       : lecture + nettoyage complet
  - detect_self_account(df)              : détecte le "compte propre" du commercial
  - _contrepartie(row, self_account)     : retourne la contrepartie d'une ligne
  - compute_reactivity(df, self_account) : indicateurs de réactivité complets

Règle d'exclusion : ALBARKA GN SARL et ALBARKA GN SARL 5 ne sont jamais
comptés comme de vraies contreparties (mouvements internes).

Règle de signe (vérifiée sur données réelles) :
  - Amount négatif : le compte propre est en "From name" → cash-out
  - Amount positif : le compte propre est en "To name"   → cash-in
"""

from pathlib import Path

import pandas as pd

EXCLUDED_NAMES = {"ALBARKA GN SARL", "ALBARKA GN SARL 5"}

# Seuil de solde bas (en dessous duquel on considère la flotte épuisée)
# avant un réapprovisionnement. Configurable en argument si besoin.
DEFAULT_LOW_BALANCE_THRESHOLD = 100_000


# ---------------------------------------------------------------------------
# Lecture + nettoyage
# ---------------------------------------------------------------------------

def load_transactions_full(source) -> pd.DataFrame:
    """
    Lit un fichier CSV de transactions Mobile Money et retourne un DataFrame
    nettoyé, signé du point de vue du compte propre du commercial.

    Le nettoyage appliqué :
      - garde les colonnes : Date, Type, From name, To name, Amount
      - garde uniquement Type == 'Transfer' et Status == 'Successful' si présent
      - exclut les lignes ALBARKA GN SARL / ALBARKA GN SARL 5 des deux côtés
      - Date réduite au jour (date Python, pas datetime)
      - Amount converti en float (suppression d'éventuels séparateurs de milliers)

    `source` peut être un chemin de fichier (str / Path) ou un objet fichier
    (ex. upload Streamlit — supporte aussi les bytes bruts).
    """
    if isinstance(source, (str, Path)):
        df = pd.read_csv(source)
    elif isinstance(source, bytes):
        import io
        df = pd.read_csv(io.BytesIO(source))
    else:
        # file-like (Streamlit UploadedFile, etc.)
        df = pd.read_csv(source)

    # Harmonise les noms de colonnes (insensible à la casse)
    df.columns = df.columns.str.strip()

    # Filtre Status = Successful si la colonne existe
    if "Status" in df.columns:
        df = df[df["Status"].str.strip() == "Successful"]

    # Garde uniquement les colonnes utiles (tolère une colonne Balance optionnelle)
    cols_required = ["Date", "Type", "From name", "To name", "Amount"]
    cols_optional = ["Balance"]
    cols_keep = [c for c in cols_required + cols_optional if c in df.columns]
    df = df[cols_keep].copy()

    # Filtre Type = Transfer
    df = df[df["Type"].str.strip() == "Transfer"]

    # Exclut les mouvements internes ALBARKA
    df = df[~df["From name"].isin(EXCLUDED_NAMES)]
    df = df[~df["To name"].isin(EXCLUDED_NAMES)]

    # Nettoyage Amount : supprime les espaces / séparateurs si c'est une chaîne
    if df["Amount"].dtype == object:
        df["Amount"] = (
            df["Amount"]
            .astype(str)
            .str.replace(r"[\s,]", "", regex=True)
            .astype(float)
        )
    else:
        df["Amount"] = df["Amount"].astype(float)

    # Date → jour seul
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Détection du compte propre du commercial
# ---------------------------------------------------------------------------

def detect_self_account(df: pd.DataFrame) -> str:
    """
    Identifie automatiquement le "compte propre" du commercial dans le listing :
    c'est le nom qui revient le plus souvent comme contrepartie, toutes
    directions confondues (From name et To name), après exclusion des noms
    déjà filtrés (ALBARKA GN SARL / ALBARKA GN SARL 5).

    Dans la pratique, ce nom correspond au compte Mobile Money du commercial
    lui-même (ex. "ALBARKA 135" pour PARFAIT), jamais au nom du fichier.

    Retourne le nom détecté (str). Lève ValueError si le DataFrame est vide.
    """
    if df.empty:
        raise ValueError("DataFrame vide — impossible de détecter le compte propre.")

    toutes_contreparties = pd.concat([df["From name"], df["To name"]], ignore_index=True)
    toutes_contreparties = toutes_contreparties[~toutes_contreparties.isin(EXCLUDED_NAMES)]
    counts = toutes_contreparties.value_counts()

    if counts.empty:
        raise ValueError("Aucune contrepartie valide trouvée dans le fichier.")

    return counts.index[0]


# ---------------------------------------------------------------------------
# Helper : contrepartie d'une ligne du point de vue du compte propre
# ---------------------------------------------------------------------------

def _contrepartie(row, self_account: str) -> str:
    """
    Retourne le nom de la contrepartie pour une ligne de transaction,
    du point de vue du compte propre (self_account).
      - si self_account est en From name → la contrepartie est To name
      - si self_account est en To name   → la contrepartie est From name
      - si aucun des deux n'est self_account, retourne From name par défaut
    """
    if row["From name"] == self_account:
        return row["To name"]
    if row["To name"] == self_account:
        return row["From name"]
    return row["From name"]


# ---------------------------------------------------------------------------
# Indicateurs de réactivité
# ---------------------------------------------------------------------------

def compute_reactivity(df: pd.DataFrame, self_account: str = None) -> dict:
    """
    Calcule les indicateurs de réactivité commerciale à partir d'un listing
    de transactions déjà nettoyé (issu de load_transactions_full).

    Indicateurs retournés :
      - transactions_par_jour       : float — moyenne quotidienne
      - clients_par_jour            : float — contreparties distinctes / jour
      - temps_mort_median_min       : float | None — médiane des écarts entre transactions (min)
      - temps_mort_max_min          : float | None — écart maximum observé (min)
      - temps_recharge_median_min   : float | None — médiane des temps de recharge de flotte (min)
      - temps_recharge_min_min      : float | None — temps de recharge le plus rapide observé (min)
      - nb_jours_actifs             : int
      - nb_transactions_total       : int

    Le calcul du temps mort se base sur l'horodatage ORIGINAL (avant réduction
    au jour) — si la colonne Date a déjà été réduite au jour (type date Python),
    le temps mort ne peut pas être calculé (retourne None).

    Le temps de recharge de flotte est calculé à partir de la colonne Balance
    si elle est présente : on détecte les moments où le solde passe sous le
    seuil DEFAULT_LOW_BALANCE_THRESHOLD puis remonte (réappro), et on mesure
    l'écart en minutes entre le dernier mouvement avant la chute et le premier
    mouvement après le réappro.
    """
    if self_account is None:
        self_account = detect_self_account(df)

    # Filtrer les lignes qui concernent le compte propre
    concerne = (df["From name"] == self_account) | (df["To name"] == self_account)
    df_own = df[concerne].copy()

    if df_own.empty:
        return {
            "transactions_par_jour": 0.0,
            "clients_par_jour": 0.0,
            "temps_mort_median_min": None,
            "temps_mort_max_min": None,
            "temps_recharge_median_min": None,
            "temps_recharge_min_min": None,
            "nb_jours_actifs": 0,
            "nb_transactions_total": 0,
        }

    # Ajoute la colonne contrepartie
    df_own["_contrepartie"] = df_own.apply(_contrepartie, axis=1, self_account=self_account)

    # --- Métriques de volume ---
    nb_total = len(df_own)
    jours_actifs = df_own["Date"].nunique()
    transactions_par_jour = round(nb_total / jours_actifs, 2) if jours_actifs else 0.0

    # Clients distincts par jour (moyenne)
    clients_par_jour_series = (
        df_own.groupby("Date")["_contrepartie"]
        .nunique()
    )
    clients_par_jour = round(float(clients_par_jour_series.mean()), 2) if not clients_par_jour_series.empty else 0.0

    # --- Temps mort ---
    # Nécessite un horodatage précis (colonne Date avec heure)
    temps_mort_median = None
    temps_mort_max = None

    date_col = df_own["Date"].iloc[0]
    has_time = isinstance(date_col, pd.Timestamp) or (
        hasattr(date_col, "hour")  # datetime possède .hour
    )

    if has_time:
        df_own_sorted = df_own.sort_values("Date")
        for jour, groupe in df_own_sorted.groupby(df_own_sorted["Date"].apply(lambda d: d.date() if hasattr(d, "date") else d)):
            if len(groupe) < 2:
                continue
            ts = pd.to_datetime(groupe["Date"]).sort_values()
            ecarts = ts.diff().dropna().dt.total_seconds() / 60  # en minutes
            if ecarts.empty:
                continue
            if temps_mort_median is None:
                ecarts_tous = ecarts
            else:
                ecarts_tous = pd.concat([ecarts_tous, ecarts])

        if temps_mort_median is not None or "ecarts_tous" in dir():
            try:
                temps_mort_median = round(float(ecarts_tous.median()), 1)
                temps_mort_max = round(float(ecarts_tous.max()), 1)
            except Exception:
                pass

    # --- Temps de recharge de flotte ---
    temps_recharge_median = None
    temps_recharge_min = None

    if "Balance" in df_own.columns and has_time:
        try:
            df_bal = df_own.sort_values("Date").copy()
            df_bal["Balance"] = pd.to_numeric(df_bal["Balance"], errors="coerce")
            df_bal = df_bal.dropna(subset=["Balance"])

            recharges = []
            i = 0
            while i < len(df_bal) - 1:
                if df_bal.iloc[i]["Balance"] < DEFAULT_LOW_BALANCE_THRESHOLD:
                    # Cherche le prochain réappro (balance remonte significativement)
                    j = i + 1
                    while j < len(df_bal) and df_bal.iloc[j]["Balance"] < DEFAULT_LOW_BALANCE_THRESHOLD:
                        j += 1
                    if j < len(df_bal):
                        t_debut = pd.Timestamp(df_bal.iloc[i]["Date"])
                        t_fin = pd.Timestamp(df_bal.iloc[j]["Date"])
                        duree = (t_fin - t_debut).total_seconds() / 60
                        if duree > 0:
                            recharges.append(duree)
                    i = j + 1
                else:
                    i += 1

            if recharges:
                temps_recharge_median = round(float(pd.Series(recharges).median()), 1)
                temps_recharge_min = round(float(min(recharges)), 1)
        except Exception:
            pass

    return {
        "transactions_par_jour": transactions_par_jour,
        "clients_par_jour": clients_par_jour,
        "temps_mort_median_min": temps_mort_median,
        "temps_mort_max_min": temps_mort_max,
        "temps_recharge_median_min": temps_recharge_median,
        "temps_recharge_min_min": temps_recharge_min,
        "nb_jours_actifs": jours_actifs,
        "nb_transactions_total": nb_total,
    }


# ---------------------------------------------------------------------------
# Auto-test CLI : python3 -m core.metrics <fichier.csv>
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage : python3 -m core.metrics <fichier_transactions.csv>")
        sys.exit(1)

    chemin = sys.argv[1]
    print(f"Chargement de {chemin} ...")
    df_test = load_transactions_full(chemin)
    print(f"{len(df_test)} transactions exploitables.")

    compte = detect_self_account(df_test)
    print(f"Compte propre détecté : {compte}")

    indicateurs = compute_reactivity(df_test, compte)
    print("\nIndicateurs de réactivité :")
    for k, v in indicateurs.items():
        print(f"  {k:<32} {v}")
