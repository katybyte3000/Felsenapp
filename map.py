import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from supabase import create_client
from dotenv import load_dotenv
import os
import math

# 🔐 Supabase-Verbindung
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ SUPABASE_URL oder SUPABASE_KEY fehlt in .env")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data
def load_rocks():
    response = supabase.table("rocks").select("id, name, latitude, longitude").execute()
    df = pd.DataFrame(response.data)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df.dropna(subset=["latitude", "longitude"])

def make_triangle(lat, lon, size=0.0005):
    # Einfaches gleichseitiges Dreieck mit Spitze nach oben
    return [
        [lat + size, lon],
        [lat - size / 2, lon - size * math.sqrt(3)/2],
        [lat - size / 2, lon + size * math.sqrt(3)/2]
    ]

def show_map(df):
    if df.empty:
        st.warning("Keine gültigen Koordinaten gefunden.")
        return

    lat_center = df["latitude"].mean()
    lon_center = df["longitude"].mean()
    m = folium.Map(location=[lat_center, lon_center], zoom_start=11)

    for _, row in df.iterrows():
        triangle = make_triangle(row["latitude"], row["longitude"])
        folium.Polygon(
            locations=triangle,
            color="blue",
            fill=True,
            fill_opacity=0.6,
            popup=row["name"],
            tooltip=f"Gipfel #{row['id']}: {row['name']}"
        ).add_to(m)

    st_folium(m, width=1000, height=600)

# UI
st.set_page_config(page_title="Gipfelkarte", layout="wide")
st.title("⛰️ Gipfel als Dreiecke")

rocks_df = load_rocks()
show_map(rocks_df)
