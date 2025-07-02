import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

# .env laden
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🧗 Begehung hinzufügen")

# 1. Sektoren laden
sectors = supabase.table("sector").select("id, name").execute().data
sectors_df = pd.DataFrame(sectors)

selected_sector = st.selectbox("1️⃣ Gebiet auswählen", sectors_df["name"])
selected_sector_id = sectors_df.loc[sectors_df["name"] == selected_sector, "id"].values[0]

# 2. Rocks aus gewähltem Gebiet
rocks = supabase.table("rocks").select("id, name, sector_id").eq("sector_id", selected_sector_id).execute().data
rocks_df = pd.DataFrame(rocks)

selected_rock = st.selectbox("2️⃣ Fels auswählen", rocks_df["name"])
selected_rock_id = rocks_df.loc[rocks_df["name"] == selected_rock, "id"].values[0]

# 3. Routen aus gewähltem Rock
routes = supabase.table("routes").select("id, name, rock_id").eq("rock_id", selected_rock_id).execute().data
routes_df = pd.DataFrame(routes)

selected_route = st.selectbox("3️⃣ Route auswählen", routes_df["name"])
selected_route_id = routes_df.loc[routes_df["name"] == selected_route, "id"].values[0]

# 4. Formular zur Begehung
st.subheader("4️⃣ Begehung eintragen")

with st.form("neue_begehung"):
    datum = st.date_input("Datum")
    partnerin = st.text_input("Partner*in")
    stil = st.selectbox("Stil", ["On-Sight", "Flash", "Rotpunkt", "Toprope"])
    kommentar = st.text_area("Kommentar")
    bewertung = st.slider("Bewertung", 0, 10, 5)
    submitted = st.form_submit_button("Begehung speichern")

# 5. Speichern
if submitted:
    try:
        response = supabase.table("ascents").insert({
            "datum": str(datum),
            "route_id": int(selected_route_id),
            "gipfel_id": int(selected_rock_id),
            "partnerin": partnerin,
            "stil": stil,
            "kommentar": kommentar,
            "bewertung": int(bewertung)
        }).execute()

        if response.data:
            st.success("✅ Begehung erfolgreich gespeichert!")
        else:
            st.error("❌ Fehler beim Speichern – evtl. Policy fehlt?")

    except Exception as e:
        st.error(f"❌ Ausnahme beim Speichern: {e}")
