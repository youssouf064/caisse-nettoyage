import io
from datetime import datetime
import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st

# Imports ReportLab pour le PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A6
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# --- CONNEXION À NEON POSTGRESQL ---
def get_connection():
    # Récupère l'URL stockée dans st.secrets
    return psycopg2.connect(st.secrets["postgres"]["url"])

# --- INITIALISATION DE LA TABLE ---
def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            date VARCHAR(10),
            type VARCHAR(20),
            categorie VARCHAR(100),
            montant NUMERIC(12, 2),
            mode_paiement VARCHAR(50),
            description TEXT
        )
    ''')
    conn.commit()
    c.close()
    conn.close()

init_db()

# --- FONCTIONS REQUÊTES ---
def ajouter_transaction(date, type_trans, categorie, montant, mode_paimet, description):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO transactions (date, type, categorie, montant, mode_paiement, description)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (date, type_trans, categorie, montant, mode_paimet, description))
    conn.commit()
    c.close()
    conn.close()

def charger_transactions():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY id DESC", conn)
    conn.close()
    return df


# --- FONCTION DE GÉNÉRATION DU PDF EN MÉMOIRE ---
def generer_pdf_recu(id_trans, date_trans, categorie, montant, mode_p, desc):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(
      buffer,
      pagesize=A6,
      rightMargin=15,
      leftMargin=15,
      topMargin=15,
      bottomMargin=15,
  )
  story = []
  styles = getSampleStyleSheet()

  title_style = ParagraphStyle(
      "TitleStyle",
      parent=styles["Heading1"],
      fontSize=13,
      alignment=1,
      textColor=colors.HexColor("#0E1117"),
      spaceAfter=5,
  )

  body_style = ParagraphStyle(
      "BodyStyle", parent=styles["Normal"], fontSize=9, leading=12
  )

  story.append(Paragraph("<b>ENTREPRISE DE NETTOYAGE</b>", title_style))
  story.append(
      Paragraph(
          "<font size=8 color='#555555'>Service de Propreté & Entretien</font>",
          ParagraphStyle("Sub", parent=title_style, fontSize=8, spaceAfter=10),
      )
  )
  story.append(
      Paragraph(
          f"<b>REÇU DE PAIEMENT N° #{id_trans}</b>",
          ParagraphStyle("Recu", parent=title_style, fontSize=10),
      )
  )
  story.append(Spacer(1, 10))

  client_note = desc if desc else "Client Passager"

  data = [
      [Paragraph("<b>Date:</b>", body_style), Paragraph(str(date_trans), body_style)],
      [
          Paragraph("<b>Service / Categorie:</b>", body_style),
          Paragraph(categorie, body_style),
      ],
      [
          Paragraph("<b>Règlement:</b>", body_style),
          Paragraph(mode_p, body_style),
      ],
      [
          Paragraph("<b>Note / Client:</b>", body_style),
          Paragraph(client_note, body_style),
      ],
      [
          Paragraph("<b>Montant réglé:</b>", body_style),
          Paragraph(f"<b>{montant:,.2f}</b>", body_style),
      ],
  ]

  t = Table(data, colWidths=[85, 135])
  t.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F2F6")),
          ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
          ("ALIGN", (0, 0), (-1, -1), "LEFT"),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
          ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
      ])
  )

  story.append(t)
  story.append(Spacer(1, 15))
  story.append(
      Paragraph(
          "<i>Merci pour votre confiance !</i>",
          ParagraphStyle("Foot", parent=body_style, alignment=1, fontSize=8),
      )
  )

  doc.build(story)
  buffer.seek(0)
  return buffer


# --- INTERFACE UTILISATEUR ---
st.title("🧹 Gestion de Caisse - Entreprise de Nettoyage")

# Barre latérale : Formulaire de Saisie
st.sidebar.header("➕ Nouvelle Transaction")

type_trans = st.sidebar.radio(
    "Type d'opération", ["Recette (Entrée)", "Dépense (Sortie)"]
)

if type_trans == "Recette (Entrée)":
  categories = [
      "Nettoyage Résidentiel",
      "Nettoyage Bureaux / Locaux",
      "Lavage Vitres",
      "Fin de Chantier",
      "Autre Recette",
  ]
else:
  categories = [
      "Achat Produits de Nettoyage",
      "Achat / Entretien Matériel",
      "Transport / Carburant",
      "Salaires / Avances",
      "Frais Généraux / Autre",
  ]

categorie = st.sidebar.selectbox("Catégorie", categories)
montant = st.sidebar.number_input(
    "Montant (MRU / FCFA / €)", min_value=0.0, step=10.0, format="%.2f"
)
mode_paiement = st.sidebar.selectbox(
    "Mode de paiement",
    ["Espèces", "Virement / Banque", "Paiement Mobile (Bankily, etc.)"],
)
date_trans = st.sidebar.date_input("Date", datetime.now())
description = st.sidebar.text_area(
    "Note / Référence Client ou Reçu",
    placeholder="Ex: Nettoyage bureau X ou achat javel",
)

if st.sidebar.button("💾 Enregistrer la transaction", use_container_width=True):
  if montant > 0:
    type_clean = "Recette" if "Recette" in type_trans else "Dépense"
    ajouter_transaction(
        date_trans.strftime("%Y-%m-%d"),
        type_clean,
        categorie,
        montant,
        mode_paiement,
        description,
    )
    st.sidebar.success("Transaction enregistrée avec succès !")
    st.rerun()
  else:
    st.sidebar.error("Le montant doit être supérieur à 0.")

# --- CHARGEMENT DES DONNÉES ---
df = charger_transactions()

# --- CALCUL DES INDICATEURS CLÉS (KPIs) ---
total_recettes = (
    df[df["type"] == "Recette"]["montant"].sum() if not df.empty else 0.0
)
total_depenses = (
    df[df["type"] == "Dépense"]["montant"].sum() if not df.empty else 0.0
)
solde_actuel = total_recettes - total_depenses

# Affichage des métriques principales
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("💰 Solde Actuel en Caisse", f"{solde_actuel:,.2f}")
kpi2.metric("📈 Total Recettes", f"{total_recettes:,.2f}")
kpi3.metric("📉 Total Dépenses", f"{total_depenses:,.2f}")

st.divider()

# --- TABLEAUX ET VISUALISATION ---
if not df.empty:
  tab1, tab2 = st.tabs(
      ["📋 Historique des Transactions", "📊 Analyses & Graphiques"]
  )

  with tab1:
    st.subheader("Journal des opérations")

    # Filtre par type
    filtre_type = st.multiselect(
        "Filtrer par type :",
        ["Recette", "Dépense"],
        default=["Recette", "Dépense"],
    )
    df_filtered = df[df["type"].isin(filtre_type)]

    # Mise en forme du tableau
    st.dataframe(
        df_filtered[[
            "id",
            "date",
            "type",
            "categorie",
            "montant",
            "mode_paiement",
            "description",
        ]],
        column_config={
            "montant": st.column_config.NumberColumn("Montant", format="%.2f"),
            "type": st.column_config.TextColumn("Type"),
        },
        hide_index=True,
        use_container_width=True,
    )

    # Exportation CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Télécharger l'historique complet (CSV)",
        data=csv,
        file_name=f"caisse_nettoyage_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    st.divider()

    # SECTION GÉNÉRATION DE REÇU PDF
    st.subheader("🧾 Générer un reçu PDF pour une recette")
    df_recettes = df[df["type"] == "Recette"]

    if not df_recettes.empty:
      recette_options = {
          f"ID #{row['id']} - {row['date']} - {row['categorie']} ({row['montant']} MRU)": row[
              "id"
          ]
          for _, row in df_recettes.iterrows()
      }

      selected_label = st.selectbox(
          "Sélectionnez la recette pour imprimer le reçu :",
          list(recette_options.keys()),
      )
      selected_id = recette_options[selected_label]

      row_selected = df_recettes[df_recettes["id"] == selected_id].iloc[0]

      pdf_bytes = generer_pdf_recu(
          id_trans=row_selected["id"],
          date_trans=row_selected["date"],
          categorie=row_selected["categorie"],
          montant=row_selected["montant"],
          mode_p=row_selected["mode_paiement"],
          desc=row_selected["description"],
      )

      st.download_button(
          label=f"📄 Télécharger le reçu PDF (ID #{selected_id})",
          data=pdf_bytes,
          file_name=f"recu_nettoyage_{selected_id}.pdf",
          mime="application/pdf",
      )
    else:
      st.info("Aucune recette enregistrée pour pouvoir éditer un reçu.")

  with tab2:
    c1, c2 = st.columns(2)

    with c1:
      st.subheader("Répartition des Dépenses")
      df_dep = df[df["type"] == "Dépense"]
      if not df_dep.empty:
        fig_dep = px.pie(df_dep, names="categorie", values="montant", hole=0.4)
        st.plotly_chart(fig_dep, use_container_width=True)
      else:
        st.info("Aucune dépense enregistrée.")

    with c2:
      st.subheader("Répartition des Recettes par Service")
      df_rec = df[df["type"] == "Recette"]
      if not df_rec.empty:
        fig_rec = px.bar(
            df_rec.groupby("categorie")["montant"].sum().reset_index(),
            x="categorie",
            y="montant",
            color="categorie",
        )
        st.plotly_chart(fig_rec, use_container_width=True)
      else:
        st.info("Aucune recette enregistrée.")

else:
  st.info(
      "Aucune transaction n'a encore été enregistrée. Utilisez le menu de"
      " gauche pour ajouter vos opérations."
  )