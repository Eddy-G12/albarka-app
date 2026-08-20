"""
pages/5_Administration.py
==========================
Volet Administration — Super Admin uniquement.

Quatre onglets :
  1. Utilisateurs         : liste, création
  2. Modification comptes : changement nom / mot de passe, désactivation
  3. Commerciaux          : téléphone, zone, dsm_name
  4. Seuils               : configuration cash in / cash out
"""

import streamlit as st

from core import db
from core.auth import require_role, show_user_badge, get_current_user

st.set_page_config(page_title="Administration — ALBARKA", layout="wide")

require_role("super_admin")
show_user_badge()

st.title("Administration")

tab_users, tab_modif, tab_com, tab_seuils = st.tabs([
    "Utilisateurs",
    "Modifier / Désactiver",
    "Commerciaux",
    "Seuils cash in / cash out",
])

role_labels = {"super_admin": "Super Admin", "admin": "Admin", "commercial": "Commercial"}

# ===========================================================================
# ONGLET 1 : LISTE + CRÉATION
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
            c4.write("Actif" if u["actif"] else "Inactif")

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
                "Nom DSM (tel qu'il apparaît dans les fichiers QR Code et SUIVI CCIAUX)"
            )
        submitted = st.form_submit_button("Créer le compte", use_container_width=True)
        if submitted:
            if not new_username or not new_nom or not new_mdp:
                st.error("Tous les champs sont obligatoires.")
            else:
                try:
                    db.create_user(new_username, new_nom, new_role, new_mdp, dsm_name=new_dsm)
                    st.success(f"Compte **{new_username}** créé avec succès.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")


# ===========================================================================
# ONGLET 2 : MODIFICATION / DÉSACTIVATION
# ===========================================================================
with tab_modif:
    st.subheader("Modifier ou désactiver un compte")

    current_user = get_current_user()
    users_all = db.list_users()

    # On ne peut pas désactiver son propre compte
    users_modif = [u for u in users_all if u["id"] != current_user["id"]]

    if not users_modif:
        st.info("Aucun autre compte à modifier.")
    else:
        user_choisi = st.selectbox(
            "Compte à modifier",
            users_modif,
            format_func=lambda u: f"{u['nom']} ({u['username']}) — {role_labels.get(u['role'], u['role'])}",
            key="sel_user_modif",
        )

        with st.container(border=True):
            st.markdown(
                f"**{user_choisi['nom']}** · `{user_choisi['username']}` · "
                f"{role_labels.get(user_choisi['role'], user_choisi['role'])} · "
                + ("Actif" if user_choisi["actif"] else "Inactif")
            )

            # --- Modification nom / mot de passe ---
            st.markdown("##### Modifier les informations")
            with st.form(f"form_modif_user_{user_choisi['id']}"):
                col1, col2 = st.columns(2)
                nouveau_nom = col1.text_input(
                    "Nouveau nom (laisser vide pour ne pas modifier)",
                    placeholder=user_choisi["nom"],
                    key=f"nom_{user_choisi['id']}",
                )
                nouveau_mdp = col2.text_input(
                    "Nouveau mot de passe (laisser vide pour ne pas modifier)",
                    type="password",
                    key=f"mdp_{user_choisi['id']}",
                )
                save = st.form_submit_button("Enregistrer les modifications", use_container_width=True)
                if save:
                    nom_val = nouveau_nom.strip() or None
                    mdp_val = nouveau_mdp.strip() or None
                    if nom_val is None and mdp_val is None:
                        st.warning("Aucune modification à enregistrer.")
                    else:
                        db.update_user(user_choisi["id"], nom=nom_val, password=mdp_val)
                        st.success("Modifications enregistrées.")
                        st.rerun()

            # --- Activation / Désactivation ---
            st.markdown("##### Statut du compte")
            label_toggle = "Désactiver ce compte" if user_choisi["actif"] else "Réactiver ce compte"
            if st.button(label_toggle, key=f"toggle_{user_choisi['id']}"):
                st.session_state[f"confirm_toggle_{user_choisi['id']}"] = True

            if st.session_state.get(f"confirm_toggle_{user_choisi['id']}"):
                action = "désactiver" if user_choisi["actif"] else "réactiver"
                st.warning(
                    f"Confirmer la **{action}** du compte de **{user_choisi['nom']}** ?"
                )
                col_y, col_n = st.columns(2)
                if col_y.button("Confirmer", key=f"conf_yes_toggle_{user_choisi['id']}", type="primary"):
                    nouveau_statut = db.toggle_user_actif(user_choisi["id"])
                    del st.session_state[f"confirm_toggle_{user_choisi['id']}"]
                    etat = "activé" if nouveau_statut else "désactivé"
                    st.success(f"Compte {etat}.")
                    st.rerun()
                if col_n.button("Annuler", key=f"conf_no_toggle_{user_choisi['id']}"):
                    del st.session_state[f"confirm_toggle_{user_choisi['id']}"]
                    st.rerun()


# ===========================================================================
# ONGLET 3 : COMMERCIAUX
# ===========================================================================
with tab_com:
    st.subheader("Gestion des commerciaux")
    st.write(
        "Modifie le numéro de téléphone, la zone ou le nom DSM d'un commercial. "
        "Le nom DSM doit correspondre exactement à ce qui figure dans les fichiers "
        "QR Code et SUIVI PERFORMANCES CCIAUX."
    )

    commerciaux = db.list_commerciaux_complet()

    if not commerciaux:
        st.info("Aucun commercial en base.")
    else:
        com_choisi = st.selectbox(
            "Commercial à modifier",
            commerciaux,
            format_func=lambda c: (
                f"{'Actif' if c['com_actif'] else 'Inactif'} — {c['dsm_name']} "
                f"({c['username'] or '—'})"
            ),
            key="sel_com_modif",
        )

        with st.container(border=True):
            # --- Badge de statut ---
            statut_com  = "Actif"  if com_choisi["com_actif"]  else "Inactif"
            statut_user = "Actif"  if com_choisi["user_actif"] else "Inactif"

            col_info1, col_info2 = st.columns([3, 1])
            with col_info1:
                st.markdown(
                    f"**{com_choisi['dsm_name']}** · "
                    f"Login : `{com_choisi['username'] or '—'}` · "
                    f"Tél : {com_choisi['telephone'] or 'Non renseigné'} · "
                    f"Zone : {com_choisi['zone'] or 'Non renseignée'}"
                )
            with col_info2:
                st.markdown(
                    f"Compte : {statut_user}  \n"
                    f"Commercial : {statut_com}"
                )

            st.markdown("---")

            # --- Formulaire modification téléphone / zone / dsm_name ---
            st.markdown("##### Informations")
            with st.form(f"form_com_{com_choisi['id']}"):
                col1, col2, col3 = st.columns(3)
                nouveau_tel = col1.text_input(
                    "Téléphone",
                    value=com_choisi["telephone"] or "",
                    placeholder="ex. 699000000",
                    key=f"tel_{com_choisi['id']}",
                )
                nouvelle_zone = col2.text_input(
                    "Zone",
                    value=com_choisi["zone"] or "",
                    placeholder="ex. Zone Nord",
                    key=f"zone_{com_choisi['id']}",
                )
                nouveau_dsm = col3.text_input(
                    "Nom DSM",
                    value=com_choisi["dsm_name"],
                    help="Doit correspondre exactement aux fichiers sources (QR Code, SUIVI CCIAUX).",
                    key=f"dsm_{com_choisi['id']}",
                )
                save_com = st.form_submit_button("Enregistrer les modifications", use_container_width=True)
                if save_com:
                    tel_val  = nouveau_tel.strip()         or None
                    zone_val = nouvelle_zone.strip()       or None
                    dsm_val  = nouveau_dsm.strip().upper() if nouveau_dsm.strip() else None
                    try:
                        db.update_commercial(
                            com_choisi["id"],
                            telephone=tel_val,
                            zone=zone_val,
                            dsm_name=dsm_val,
                        )
                        st.success(f"Informations de **{com_choisi['dsm_name']}** mises à jour.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

            # --- Activation / Désactivation du commercial ---
            st.markdown("##### Statut du commercial")

            if com_choisi["com_actif"]:
                label_toggle_com = "Désactiver ce commercial"
                info_toggle = (
                    "Désactiver bloque également la connexion du compte lié. "
                    "Les données historiques sont conservées."
                )
            else:
                label_toggle_com = "Réactiver ce commercial"
                info_toggle = "Réactiver permet à nouveau la connexion du compte lié."

            st.caption(info_toggle)

            if st.button(label_toggle_com, key=f"toggle_com_{com_choisi['id']}"):
                st.session_state[f"confirm_toggle_com_{com_choisi['id']}"] = True

            if st.session_state.get(f"confirm_toggle_com_{com_choisi['id']}"):
                action_com = "désactiver" if com_choisi["com_actif"] else "réactiver"
                st.warning(
                    f"Confirmer la **{action_com}** du commercial **{com_choisi['dsm_name']}** "
                    + ("(le compte sera aussi désactivé) ?" if com_choisi["com_actif"]
                       else "(le compte sera aussi réactivé) ?")
                )
                col_y, col_n = st.columns(2)
                if col_y.button(
                    "Confirmer",
                    key=f"conf_yes_com_{com_choisi['id']}",
                    type="primary",
                ):
                    nouveau_statut = db.toggle_commercial_actif(com_choisi["id"])
                    del st.session_state[f"confirm_toggle_com_{com_choisi['id']}"]
                    etat = "réactivé" if nouveau_statut else "désactivé"
                    st.success(f"Commercial {etat}. Compte utilisateur synchronisé.")
                    st.rerun()
                if col_n.button("Annuler", key=f"conf_no_com_{com_choisi['id']}"):
                    del st.session_state[f"confirm_toggle_com_{com_choisi['id']}"]
                    st.rerun()

        # --- Vue complète en tableau ---
        st.divider()
        st.markdown("**Tous les commerciaux**")
        import pandas as pd
        df_com = pd.DataFrame([
            {
                "DSM":              c["dsm_name"],
                "Login":            c["username"] or "—",
                "Téléphone":        c["telephone"] or "—",
                "Zone":             c["zone"] or "—",
                "Commercial actif": "Actif" if c["com_actif"]  else "Inactif",
                "Compte actif":     "Actif" if c["user_actif"] else "Inactif",
            }
            for c in commerciaux
        ])
        st.dataframe(df_com, hide_index=True, use_container_width=True)


# ===========================================================================
# ONGLET 4 : SEUILS
# ===========================================================================
with tab_seuils:
    st.subheader("Seuils d'alerte cash in / cash out")
    st.write(
        "Un commercial est signalé **en alerte** lorsque son cash in ou cash out "
        "du mois est inférieur au seuil fixé ici."
    )

    seuil_ci = db.get_seuil("cash_in")
    seuil_co = db.get_seuil("cash_out")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Seuil cash in actuel",
                  f"{seuil_ci['valeur']:,.0f} FCFA" if seuil_ci else "Non défini")
    with col2:
        st.metric("Seuil cash out actuel",
                  f"{seuil_co['valeur']:,.0f} FCFA" if seuil_co else "Non défini")

    st.divider()
    with st.form("form_seuils"):
        col1, col2 = st.columns(2)
        nouveau_ci = col1.number_input(
            "Nouveau seuil cash in (FCFA)",
            min_value=0, step=10000,
            value=int(seuil_ci["valeur"]) if seuil_ci else 0,
        )
        nouveau_co = col2.number_input(
            "Nouveau seuil cash out (FCFA)",
            min_value=0, step=10000,
            value=int(seuil_co["valeur"]) if seuil_co else 0,
        )
        mois_seuil = st.text_input(
            "Mois concerné (optionnel, format AAAA-MM — laisser vide pour un seuil global)",
            placeholder="ex. 2026-08",
        )
        submitted = st.form_submit_button("Enregistrer les seuils", use_container_width=True)
        if submitted:
            user = st.session_state.get("albarka_user")
            mois_val = mois_seuil.strip() or None
            db.set_seuil("cash_in",  nouveau_ci, mois=mois_val, created_by=user["id"] if user else None)
            db.set_seuil("cash_out", nouveau_co, mois=mois_val, created_by=user["id"] if user else None)
            st.success("Seuils enregistrés.")
            st.rerun()

    # Historique des seuils configurés
    with st.expander("Historique des seuils"):
        conn = db.get_connection()
        rows = conn.execute("""
            SELECT s.type_flux, s.valeur, s.mois, s.created_at, u.nom AS cree_par
            FROM seuils s
            LEFT JOIN utilisateurs u ON u.id = s.created_by
            ORDER BY s.created_at DESC
        """).fetchall()
        conn.close()
        if rows:
            import pandas as pd
            df_seuils = pd.DataFrame([dict(r) for r in rows])
            df_seuils.columns = ["Type", "Valeur (FCFA)", "Mois", "Créé le", "Créé par"]
            df_seuils["Valeur (FCFA)"] = df_seuils["Valeur (FCFA)"].map("{:,.0f}".format)
            df_seuils["Mois"] = df_seuils["Mois"].fillna("Global")
            st.dataframe(df_seuils, hide_index=True, use_container_width=True)
        else:
            st.info("Aucun seuil configuré.")
