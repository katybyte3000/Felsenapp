import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import math

# Lade Umgebungsvariablen
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    st.error("Fehler: SUPABASE_URL oder SUPABASE_KEY wurden nicht gefunden. Stellen Sie sicher, dass Ihre .env-Datei korrekt ist.")
    st.stop()

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Fehler beim Erstellen des Supabase-Clients: {e}")
    st.stop()

def make_triangle(lat, lon, size=0.001):
    if pd.isna(lat) or pd.isna(lon) or pd.isna(size) or size <= 0:
        return None
    try:
        return [
            [lat + size, lon],
            [lat - size / 2, lon - size * math.sqrt(3)/2],
            [lat - size / 2, lon + size * math.sqrt(3)/2],
        ]
    except TypeError:
        return None

@st.cache_data
def fetch_data():
    try:
        sectors = pd.DataFrame(supabase.table("sector").select("id, name").execute().data)
        sectors['id'] = sectors['id'].astype(int)

        rocks = pd.DataFrame(supabase.table("rocks").select("id, name, sector_id, latitude, longitude").range(0, 5000).execute().data)
        rocks['id'] = rocks['id'].astype(int)
        rocks['sector_id'] = rocks['sector_id'].astype(int)

        rocks = rocks.merge(sectors, left_on="sector_id", right_on="id", suffixes=("_rock", "_sector"))
        rocks.rename(columns={"name_sector": "gebiet", "name_rock": "name", "id_rock": "id"}, inplace=True)
        rocks.drop(columns=["id_sector"], errors='ignore', inplace=True)

        # Alle rock_ids aus routes laden (mehr als 1000)
        def fetch_all_routes_column():
            full_data = []
            step = 1000
            for start in range(0, 25000, step):
                end = start + step - 1
                chunk = supabase.table("routes").select("rock_id, grade").range(start, end).execute().data
                if not chunk:
                    break
                full_data.extend(chunk)
            return pd.DataFrame(full_data)

        routes_for_count = fetch_all_routes_column()
        routes_for_count['rock_id'] = routes_for_count['rock_id'].astype(int)
        routes_for_count['grade'] = pd.to_numeric(routes_for_count['grade'], errors='coerce')

        routes = pd.DataFrame(supabase.table("routes").select("id, rock_id, stern").range(0, 5000).execute().data)
        routes['id'] = routes['id'].astype(int)
        routes['rock_id'] = routes['rock_id'].astype(int)
        routes['stern'] = routes.get('stern', False).astype(bool)

        ascents = pd.DataFrame(supabase.table("ascents").select("id, gipfel_id, route_id, bewertung, kommentar").execute().data)
        ascents.rename(columns={"id": "ascent_id"}, inplace=True)
        ascents['gipfel_id'] = ascents['gipfel_id'].astype(int)
        ascents['route_id'] = pd.to_numeric(ascents['route_id'], errors='coerce').fillna(0).astype(int)
        ascents['bewertung'] = pd.to_numeric(ascents['bewertung'], errors='coerce').fillna(0).astype(int)

        return rocks, routes, ascents, routes_for_count
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def app():
    st.set_page_config(layout="wide")
    st.title("Gipfelkarte: Felsen finden")

    rocks, routes, ascents, routes_for_count = fetch_data()

    if rocks.empty or routes.empty:
        st.warning("Keine Felsen oder Routen geladen.")
        return

    st.sidebar.title("Filter")

    st.sidebar.write(f"🪨 Geladene Felsen: {len(rocks)}")

    gebiete = sorted(rocks["gebiet"].dropna().unique())
    selected_gebiet = st.sidebar.selectbox("Gebiet auswählen", ["Alle"] + gebiete)

    grade_filter_enabled = st.sidebar.checkbox("Nach Schwierigkeitsgrad filtern")
    if grade_filter_enabled:
        grade_range = st.sidebar.slider("Schwierigkeitsgradbereich (1-12)", 1, 12, (1, 12))
        grad_filter = routes_for_count[routes_for_count['grade'].between(grade_range[0], grade_range[1])]
        allowed_rock_ids = grad_filter['rock_id'].unique()
        rocks = rocks[rocks['id'].isin(allowed_rock_ids)]

    show_done = st.sidebar.checkbox("Nur begangene Felsen anzeigen")
    show_not_done = st.sidebar.checkbox("Nur unbegangene Felsen anzeigen")

    rocks = rocks.copy()
    if selected_gebiet != "Alle":
        rocks = rocks[rocks["gebiet"] == selected_gebiet]

    route_counts = routes_for_count.groupby("rock_id").size().reset_index(name="anzahl_routen")
    rocks = rocks.merge(route_counts, left_on="id", right_on="rock_id", how="left")
    rocks["anzahl_routen"] = rocks["anzahl_routen"].fillna(0).astype(int)

    star_rocks = routes.groupby("rock_id")["stern"].any().reset_index().rename(columns={"stern": "rock_has_star"})
    rocks = rocks.merge(star_rocks, left_on="id", right_on="rock_id", how="left")
    rocks["rock_has_star"] = rocks["rock_has_star"].fillna(False).astype(bool)

    done_rock_ids = ascents["gipfel_id"].unique()
    st.sidebar.write(f"✅ Begangene Felsen (distinct gipfel_id): {len(done_rock_ids)}")
    rocks["has_done_route"] = rocks["id"].isin(done_rock_ids)

    if show_done:
        rocks = rocks[rocks["has_done_route"] == True]
    elif show_not_done:
        rocks = rocks[rocks["has_done_route"] == False]

    st.subheader("Interaktive Karte")
    filtered = rocks.dropna(subset=["latitude", "longitude"])

    st.sidebar.write(f"🗺️ Sichtbare Felsen nach Filter: {len(filtered)}")

    if filtered.empty:
        st.info("Keine gültigen Koordinaten verfügbar.")
        return

    lat_center = filtered["latitude"].mean()
    lon_center = filtered["longitude"].mean()

    m = folium.Map(location=[lat_center, lon_center], zoom_start=11, tiles='CartoDB Positron')

    for _, row in filtered.iterrows():
        anzahl = row.get("anzahl_routen", 0)
        if anzahl <= 5:
            größe = 0.0015
        elif anzahl <= 10:
            größe = 0.0022
        else:
            größe = 0.003

        fill_color = "red"
        if row.get("rock_has_star", False):
            fill_color = "purple"
        if row.get("has_done_route", False):
            fill_color = "black"

        coords = make_triangle(row["latitude"], row["longitude"], größe)
        if coords:
            tooltip = f"""
            <b>{row['name']}</b><br>
            Routen: {int(anzahl)}<br>
            Gebiet: {row['gebiet']}<br>
            Star: {'⭐' if row.get('rock_has_star') else '—'}<br>
            Begehung: {'✅' if row.get('has_done_route') else '❌'}
            """
            folium.Polygon(
                locations=coords,
                color=None,
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.89,
                tooltip=folium.Tooltip(tooltip, sticky=True)
            ).add_to(m)

    st_folium(m, width=1400, height=600)

if __name__ == "__main__":
    app()
