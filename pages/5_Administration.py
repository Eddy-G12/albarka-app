"""
pages/5_Administration.py — v2
================================
Volet Administration — Super Admin uniquement.

Onglets :
  1. Utilisateurs         : liste, création
  2. Modifier / Désactiver : changement nom / mot de passe, désactivation
  3. Commerciaux          : téléphone, zone, dsm_name, activation
  4. Aliases              : alias CSV de chaque commercial (ex. ALBARKA 135 pour PARFAIT)
  5. Seuils               : seuils cash in / cash out
"""

import streamlit as st
import pandas as pd

from core import db
from core.auth import require_role, show_user_badge, get_current_user
from core.ui import apply_theme, show_page_header

apply_theme()
require_role("super_admin")
show_user_badge()

show_page_header("Administration", "Gestion des utilisateurs, aliases et paramètres")
st.divider()

tab_users, tab_modif, tab_com, tab_aliases, tab_seuils = st.tabs([
    "Utilisateurs",
    "Modifier / Désactiver",
    "Commerciaux",
    "Aliases CSV",
    "Seuils cash in / cash out",
])

role_labels = {"super_admin": "Super Admin", "admin": "Admin", "commercial": "Commercial"}


# ===========================================================================
# ONGLET 1 — UTILISATEURS
# ===========================================================================
with tab_users:
    st.subheader("Comptes utilisateurs")

    users = db.list_users()
    for u in users:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            c1.markdown(f"**{u['nom']}**")
            c2.write(u["username"])
            c3.write(role_labels.get(u["role"], u["role"]))
            c4.write("Actif" if u["actif"] else "⛔ Inactif")

    st.divider()
    st.subheader("Créer un compte")

    with st.form("form_new_user"):
        col1, col2 = st.columns(2)
        new_username = col1.text_input("Identifiant (login)")
        new_nom      = col2.text_input("Nom complet")
        col3, col4   = st.columns(2)
        new_role     = col3.selectbox("Rôle", ["commercial", "admin", "super_admin"])
        new_mdp      = col4.text_input("Mot de passe", type="password")
        new_dsm      = None
        if new_role == "commercial":
            new_dsm = st.text_input(
                "Nom DSM (tel qu'il apparaît dans les fichiers QR Code)"
            )
        submitted = st.form_submit_button("Créer le compte", use_container_width=True)
        if submitted:
            if not new_username or not new_nom or not new_mdp:
                st.error("Tous les champs sont obligatoires.")
            else:
                try:
                    db.create_user(new_username, new_nom, new_role, new_mdp, dsm_name=new_dsm)
                    st.success(f"Compte **{new_username}** créé.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")


# ===========================================================================
# ONGLET 2 — MODIFIER / DÉSACTIVER
# ===========================================================================
with tab_modif:
    st.subheader("Modifier ou désactiver un compte")

    current_user = get_current_user()
    users_all    = db.list_users()
    users_modif  = [u for u in users_all if u["id"] != current_user["id"]]

    if not users_modif:
        st.info("Aucun autre compte à modifier.")
    else:
        user_choisi = st.selectbox(
            "Compte à modifier",
            users_modif,
            format_func=lambda u: (
                f"{u['nom']} ({u['username']}) — "
                f"{role_labels.get(u['role'], u['role'])}"
            ),
            key="sel_user_modif",
        )

        with st.container(border=True):
            st.markdown(
                f"**{user_choisi['nom']}** · `{user_choisi['username']}` · "
                f"{role_labels.get(user_choisi['role'], user_choisi['role'])} · "
                + ("Actif" if user_choisi["actif"] else "⛔ Inactif")
            )

            st.markdown("##### Modifier les informations")
            with st.form(f"form_modif_{user_choisi['id']}"):
                col1, col2 = st.columns(2)
                nouveau_nom = col1.text_input(
                    "Nouveau nom (vide = inchangé)",
                    key=f"nom_{user_choisi['id']}",
                )
                nouveau_mdp = col2.text_input(
                    "Nouveau mot de passe (vide = inchangé)",
                    type="password",
                    key=f"mdp_{user_choisi['id']}",
                )
                save = st.form_submit_button("Enregistrer", use_container_width=True)
                if save:
                    nom_val = nouveau_nom.strip() or None
                    mdp_val = nouveau_mdp.strip() or None
                    if nom_val is None and mdp_val is None:
                        st.warning("Aucune modification à enregistrer.")
                    else:
                        db.update_user(user_choisi["id"], nom=nom_val, password=mdp_val)
                        st.success("Modifications enregistrées.")
                        st.rerun()

            st.markdown("##### Statut du compte")
            lbl_toggle = "Désactiver" if user_choisi["actif"] else "Réactiver"
            if st.button(lbl_toggle, key=f"toggle_{user_choisi['id']}"):
                st.session_state[f"conf_toggle_{user_choisi['id']}"] = True

            if st.session_state.get(f"conf_toggle_{user_choisi['id']}"):
                action = "désactiver" if user_choisi["actif"] else "réactiver"
                st.warning(f"Confirmer la **{action}** du compte de **{user_choisi['nom']}** ?")
                c_y, c_n = st.columns(2)
                if c_y.button("Confirmer", key=f"conf_y_t_{user_choisi['id']}", type="primary"):
                    db.toggle_user_actif(user_choisi["id"])
                    st.session_state.pop(f"conf_toggle_{user_choisi['id']}", None)
                    st.rerun()
                if c_n.button("Annuler", key=f"conf_n_t_{user_choisi['id']}"):
                    st.session_state.pop(f"conf_toggle_{user_choisi['id']}", None)
                    st.rerun()


# ===========================================================================
# ONGLET 3 — COMMERCIAUX
# ===========================================================================
with tab_com:
    st.subheader("Gestion des commerciaux")
    st.caption(
        "Le nom DSM doit correspondre exactement aux fichiers QR Code. "
        "L'alias CSV se configure dans l'onglet **Aliases CSV**."
    )

    commerciaux = db.list_commerciaux_complet()

    if not commerciaux:
        st.info("Aucun commercial en base.")
    else:
        com_choisi = st.selectbox(
            "Commercial à modifier",
            commerciaux,
            format_func=lambda c: (
                f"{'✅' if c['com_actif'] else '⛔'} {c['dsm_name']} "
                f"({c['username'] or '—'}) — alias : {c.get('alias_csv') or 'aucun'}"
            ),
            key="sel_com_modif",
        )

        with st.container(border=True):
            st.markdown(
                f"**{com_choisi['dsm_name']}** · Login : `{com_choisi['username'] or '—'}` · "
                f"Tél : {com_choisi['telephone'] or '—'} · Zone : {com_choisi['zone'] or '—'} · "
                f"Alias CSV : **{com_choisi.get('alias_csv') or 'aucun'}**"
            )

            st.markdown("##### Informations")
            with st.form(f"form_com_{com_choisi['id']}"):
                col1, col2, col3 = st.columns(3)
                nouveau_tel  = col1.text_input("Téléphone",
                    value=com_choisi["telephone"] or "", key=f"tel_{com_choisi['id']}")
                nouvelle_zone = col2.text_input("Zone",
                    value=com_choisi["zone"] or "", key=f"zone_{com_choisi['id']}")
                nouveau_dsm  = col3.text_input("Nom DSM",
                    value=com_choisi["dsm_name"], key=f"dsm_{com_choisi['id']}")
                if st.form_submit_button("Enregistrer", use_container_width=True):
                    try:
                        db.update_commercial(
                            com_choisi["id"],
                            telephone=nouveau_tel.strip() or None,
                            zone=nouvelle_zone.strip() or None,
                            dsm_name=nouveau_dsm.strip().upper() or None,
                        )
                        st.success("Informations mises à jour.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

            st.markdown("##### Statut")
            lbl = "Désactiver" if com_choisi["com_actif"] else "Réactiver"
            caption = (
                "Désactiver bloque aussi la connexion du compte lié."
                if com_choisi["com_actif"]
                else "Réactiver restaure aussi la connexion du compte lié."
            )
            st.caption(caption)
            if st.button(lbl, key=f"toggle_com_{com_choisi['id']}"):
                st.session_state[f"conf_com_{com_choisi['id']}"] = True

            if st.session_state.get(f"conf_com_{com_choisi['id']}"):
                action = "désactiver" if com_choisi["com_actif"] else "réactiver"
                st.warning(f"Confirmer la **{action}** de **{com_choisi['dsm_name']}** ?")
                c_y, c_n = st.columns(2)
                if c_y.button("Confirmer", key=f"conf_yc_{com_choisi['id']}", type="primary"):
                    db.toggle_commercial_actif(com_choisi["id"])
                    st.session_state.pop(f"conf_com_{com_choisi['id']}", None)
                    st.rerun()
                if c_n.button("Annuler", key=f"conf_nc_{com_choisi['id']}"):
                    st.session_state.pop(f"conf_com_{com_choisi['id']}", None)
                    st.rerun()

        # Tableau récap
        st.divider()
        df_com = pd.DataFrame([
            {
                "DSM":     c["dsm_name"],
                "Login":   c["username"] or "—",
                "Tél":     c["telephone"] or "—",
                "Zone":    c["zone"] or "—",
                "Alias CSV": c.get("alias_csv") or "—",
                "Commercial": "Actif" if c["com_actif"] else "Inactif",
                "Compte":     "Actif" if c["user_actif"] else "Inactif",
            }
            for c in commerciaux
        ])
        st.dataframe(df_com, hide_index=True, use_container_width=True)


# ===========================================================================
# ONGLET 4 — ALIASES CSV
# ===========================================================================
with tab_aliases:
    st.subheader("Aliases des commerciaux dans les fichiers CSV")
    st.write(
        "L'alias est le nom tel qu'il apparaît dans les fichiers CSV de transactions "
        "Mobile Money pour identifier le compte propre du commercial. "
        "Il est utilisé pour le calcul de l'appro/destockage et le stockage des clients servis. "
        "Un seul alias actif à la fois par commercial. Laisser vide = pas d'alias (appro non calculé)."
    )

    # Tableau récap actuel
    aliases_actuels = db.list_aliases()
    commerciaux_tous = db.list_commerciaux_complet()

    # Indexer par commercial_id pour affichage rapide
    alias_par_id = {a["commercial_id"]: a["alias"] for a in aliases_actuels}

    st.markdown("#### Aliases actuels")
    rows_alias = []
    for c in commerciaux_tous:
        rows_alias.append({
            "DSM":       c["dsm_name"],
            "Alias CSV": alias_par_id.get(c["id"]) or "— (aucun)",
            "Statut":    "Actif" if c["com_actif"] else "Inactif",
        })
    st.dataframe(pd.DataFrame(rows_alias), hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("#### Modifier un alias")

    com_alias = st.selectbox(
        "Commercial",
        commerciaux_tous,
        format_func=lambda c: (
            f"{c['dsm_name']} — alias actuel : {alias_par_id.get(c['id']) or 'aucun'}"
        ),
        key="sel_com_alias",
    )

    alias_actuel = alias_par_id.get(com_alias["id"], "")
    nouvel_alias = st.text_input(
        "Alias CSV (laisser vide pour supprimer l'alias)",
        value=alias_actuel,
        key=f"alias_input_{com_alias['id']}",
    )

    if st.button("Enregistrer l'alias", key="btn_save_alias"):
        db.set_alias(com_alias["id"], nouvel_alias.strip() or None)
        if nouvel_alias.strip():
            st.success(
                f"Alias de **{com_alias['dsm_name']}** mis à jour : "
                f"**{nouvel_alias.strip()}**"
            )
        else:
            st.success(f"Alias de **{com_alias['dsm_name']}** supprimé.")
        st.rerun()

    # Exemples pré-remplis pour référence
    st.divider()
    st.markdown("#### Référence — aliases par défaut")
    st.dataframe(
        pd.DataFrame([
            {"Commercial": "PARFAIT",  "Alias attendu": "ALBARKA 135"},
            {"Commercial": "STEPHANE", "Alias attendu": "ALBARKA 85"},
            {"Commercial": "ANTOINE",  "Alias attendu": "ALBARKA 72"},
            {"Commercial": "ERVE",     "Alias attendu": "ALBARKA 89"},
            {"Commercial": "EWANE",    "Alias attendu": "ALBARKA 71"},
            {"Commercial": "FRANCK",   "Alias attendu": "— (aucun)"},
            {"Commercial": "PROSPER",  "Alias attendu": "— (aucun)"},
            {"Commercial": "CESAIRE",  "Alias attendu": "— (aucun)"},
        ]),
        hide_index=True, use_container_width=True,
    )


# ===========================================================================
# ONGLET 5 — SEUILS
# ===========================================================================
with tab_seuils:
    st.subheader("Seuils d'alerte cash in / cash out")
    st.caption(
        "Un POS est signalé en alerte lorsque son cash in ou cash out du mois "
        "est inférieur au seuil fixé ici."
    )

    seuil_ci = db.get_seuil("cash_in")
    seuil_co = db.get_seuil("cash_out")

    col1, col2 = st.columns(2)
    col1.metric("Seuil cash in actuel",
                f"{seuil_ci['valeur']:,.0f} FCFA" if seuil_ci else "Non défini")
    col2.metric("Seuil cash out actuel",
                f"{seuil_co['valeur']:,.0f} FCFA" if seuil_co else "Non défini")

    st.divider()
    with st.form("form_seuils"):
        col1, col2 = st.columns(2)
        nouveau_ci = col1.number_input(
            "Seuil cash in (FCFA)", min_value=0, step=10000,
            value=int(seuil_ci["valeur"]) if seuil_ci else 0,
        )
        nouveau_co = col2.number_input(
            "Seuil cash out (FCFA)", min_value=0, step=10000,
            value=int(seuil_co["valeur"]) if seuil_co else 0,
        )
        mois_seuil = st.text_input(
            "Mois concerné (AAAA-MM — laisser vide pour un seuil global)",
        )
        if st.form_submit_button("Enregistrer les seuils", use_container_width=True):
            u = st.session_state.get("albarka_user")
            mois_val = mois_seuil.strip() or None
            db.set_seuil("cash_in",  nouveau_ci, mois=mois_val, created_by=u["id"] if u else None)
            db.set_seuil("cash_out", nouveau_co, mois=mois_val, created_by=u["id"] if u else None)
            st.success("Seuils enregistrés.")
            st.rerun()

    with st.expander("Historique des seuils"):
        conn = db.get_connection()
        rows = conn.execute("""
            SELECT s.type_flux, s.valeur, s.mois, s.created_at, u.nom AS cree_par
            FROM seuils s LEFT JOIN utilisateurs u ON u.id = s.created_by
            ORDER BY s.created_at DESC
        """).fetchall()
        conn.close()
        if rows:
            df_s = pd.DataFrame([dict(r) for r in rows])
            df_s.columns = ["Type","Valeur (FCFA)","Mois","Créé le","Créé par"]
            df_s["Valeur (FCFA)"] = df_s["Valeur (FCFA)"].map("{:,.0f}".format)
            df_s["Mois"] = df_s["Mois"].fillna("Global")
            st.dataframe(df_s, hide_index=True, use_container_width=True)
        else:
            st.info("Aucun seuil configuré.")
