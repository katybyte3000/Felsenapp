import streamlit as st
from supabase import create_client, Client
import pandas as pd
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
if not url or not key:
    st.error("Supabase-Zugangsdaten fehlen.")
    st.stop()

# Supabase-Client
supabase: Client = create_client(url, key)

@st.cache_data
def load_data():
    try:
        # Sektoren laden
        sectors_response = supabase.table("sector").select("id, name").execute()
        sectors_df = pd.DataFrame(sectors_response.data)

        # Rocks laden
        rocks_response = supabase.table("rocks").select("id, sector_id").execute()
        rocks_df = pd.DataFrame(rocks_response.data)

        # Datentypen sichern
        sectors_df["id"] = sectors_df["id"].astype(int)
        rocks_df["sector_id"] = rocks_df["sector_id"].astype(int)

        return sectors_df, rocks_df
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return pd.DataFrame(), pd.DataFrame()

def app():
    st.title("Gebiete & Anzahl Felsen")

    sectors_df, rocks_df = load_data()

    if sectors_df.empty or rocks_df.empty:
        st.warning("Keine Daten verfügbar.")
        return

    # Zähle Rocks je Sektor
    anzahl_df = rocks_df.groupby("sector_id").size().reset_index(name="Anzahl_Felsen")

    # Merge mit Sektor-Namen
    merged = sectors_df.merge(anzahl_df, left_on="id", right_on="sector_id", how="left")
    merged["Anzahl_Felsen"] = merged["Anzahl_Felsen"].fillna(0).astype(int)

    # Ausgabe
    st.dataframe(merged[["name", "Anzahl_Felsen"]].sort_values(by="Anzahl_Felsen", ascending=False))

# App starten
if __name__ == "__main__":
    app()
