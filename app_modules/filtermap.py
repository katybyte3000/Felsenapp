import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import math

# --- ✅ FINALES PLOT-FARBSCHEMA (PASSEND ZU app.py, WCAG-OPTIMIERT) ---

# === MARKENFARBEN ===
PLOT_HIGHLIGHT_COLOR = "#359bca"     # Primärakzent – Cyan (Vorstieg, Highlights)
PLOT_SECONDARY_COLOR = "#9bca35"     # Sekundärakzent – Limette (Nachstieg)
PLOT_NEGATIVE_COLOR = "#ca359b"      # Negativ/Kritisch – Magenta
PLOT_BG_COLOR = "#F7F7F7"            # Neutraler Hintergrund – Hellgrau

# === TEXT & KONTRASTE ===
PLOT_TEXT_COLOR = "#111111"          # Maximaler Kontrast auf Hellgrau
PLOT_MUTED_TEXT = "#4D4D4D"          # Gedämpfter Text (optional)
PLOT_OUTLINE_COLOR = "#111111"       # Klare schwarze Outlines




    # --- ✅ CSS für Sidebar-Widgets und Lesbarkeit ---
st.markdown(f"""
    <style>
    /* === Sidebar Hintergrund + Textfarben === */
            
[data-testid="stSidebar"] {{
    background-color: #f8f8ff !important;  /* helles Grau */
    color: #FFFFFF !important;
}}

            
            
/* Sidebar Überschriften / Titel */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6 {{
    color: #FFFFFF !important;
    font-family: 'Oswald', sans-serif !important;
    font-weight: 700 !important;
}}

/* Sidebar Labels, Checkboxen, Radio Buttons */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCheckbox label,
[data-testid="stSidebar"] .stRadio label {{
    color: #FFFFFF !important;
    font-family: 'Noto Sans', sans-serif !important;
    font-weight: 700 !important;
}}

/* Sidebar Radio Button Hover (nur Hintergrund) */
[data-testid="stSidebar"] .stRadio div[data-baseweb="radio"]:hover label {{
    background-color: #5A7DA3 !important;
}}

/* Sidebar Buttons */
[data-testid="stSidebar"] button {{
    background-color: #5A7DA3 !important;
    color: #FFFFFF !important;
    border: 2px solid #5A7DA3 !important;
    border-radius: 6px;
}}

[data-testid="stSidebar"] button:hover {{
    background-color: #EBEBEB !important;
    color: #FFFFFF !important;
}}
    </style>
    """, unsafe_allow_html=True)


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


def fetch_data(_supabase_client: Client, user_id: str):
    try:
        sectors = pd.DataFrame(_supabase_client.table("sector").select("id, name").execute().data)
        sectors['id'] = sectors['id'].astype(int)

        rocks = pd.DataFrame(_supabase_client.table("rocks").select("id, name, sector_id, latitude, longitude, hoehe").range(0, 5000).execute().data)
        rocks['id'] = rocks['id'].astype(int)
        rocks['sector_id'] = rocks['sector_id'].astype(int)
        rocks = rocks.merge(sectors, left_on="sector_id", right_on="id", suffixes=("_rock", "_sector"))
        rocks.rename(columns={"name_sector": "gebiet", "name_rock": "name", "id_rock": "id"}, inplace=True)
        rocks.drop(columns=["id_sector"], errors='ignore', inplace=True)

        def fetch_all_routes_column_internal():
            full_data = []
            step = 1000
            for start in range(0, 25000, step):
                end = start + step - 1
                chunk = _supabase_client.table("routes").select("rock_id, grade, name, number").range(start, end).execute().data
                if not chunk:
                    break
                full_data.extend(chunk)
            return pd.DataFrame(full_data)

        routes_full_data = fetch_all_routes_column_internal()
        routes_full_data['rock_id'] = routes_full_data['rock_id'].astype(int)
        routes_full_data['grade'] = pd.to_numeric(routes_full_data['grade'], errors='coerce')

        routes_for_stars = pd.DataFrame(_supabase_client.table("routes").select("id, rock_id, stern").range(0, 5000).execute().data)
        routes_for_stars['id'] = routes_for_stars['id'].astype(int)
        routes_for_stars['rock_id'] = routes_for_stars['rock_id'].astype(int)
        routes_for_stars['stern'] = routes_for_stars.get('stern', False).astype(bool)

        if user_id:
            ascents = pd.DataFrame(_supabase_client.table("ascents").select("id, gipfel_id, route_id, bewertung, kommentar").eq("user_id", user_id).execute().data)
        else:
            ascents = pd.DataFrame()

        ascents.rename(columns={"id": "ascent_id"}, inplace=True)
        ascents['gipfel_id'] = pd.to_numeric(ascents['gipfel_id'], errors='coerce').fillna(0).astype(int)
        ascents['route_id'] = pd.to_numeric(ascents['route_id'], errors='coerce').fillna(0).astype(int)
        ascents['bewertung'] = pd.to_numeric(ascents['bewertung'], errors='coerce').fillna(0).astype(int)

        return rocks, routes_for_stars, ascents, routes_full_data
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def show_filter_map_page(supabase_client: Client):
    st.markdown('<div class="headline-fonts">Gipfelkarte: Felsen finden</div>', unsafe_allow_html=True)

    rocks, routes_for_stars, ascents, routes_full_data = fetch_data(supabase_client, st.session_state.get("user_id"))
    if rocks.empty:
        st.warning("Keine Felsen zum Anzeigen verfügbar. Überprüfen Sie Ihre Datenquelle.")
        return


    # --- Sidebar Widgets ---
    st.sidebar.title("Filter")
    st.sidebar.write(f"🪨 Geladene Felsen: {len(rocks)}")

    gebiete = sorted(rocks["gebiet"].dropna().unique())
    selected_gebiet = st.sidebar.selectbox("Gebiet auswählen", ["Alle"] + gebiete)

    grade_filter_enabled = st.sidebar.checkbox("Nach Schwierigkeitsgrad filtern")
    if grade_filter_enabled:
        grade_range = st.sidebar.slider("Schwierigkeitsgradbereich (1-12)", 1, 12, (1, 12))
        grad_filter = routes_full_data[routes_full_data['grade'].between(grade_range[0], grade_range[1])]
        allowed_rock_ids = grad_filter['rock_id'].unique()
        rocks = rocks[rocks['id'].isin(allowed_rock_ids)]

    if selected_gebiet != "Alle":
        rocks = rocks[rocks["gebiet"] == selected_gebiet]

    route_counts = routes_full_data.groupby("rock_id").size().reset_index(name="anzahl_routen")
    rocks = rocks.merge(route_counts, left_on="id", right_on="rock_id", how="left")
    rocks["anzahl_routen"] = rocks["anzahl_routen"].fillna(0).astype(int)

    star_rocks = routes_for_stars.groupby("rock_id")["stern"].any().reset_index().rename(columns={"stern": "rock_has_star"})
    rocks = rocks.merge(star_rocks, left_on="id", right_on="rock_id", how="left")
    rocks["rock_has_star"] = rocks["rock_has_star"].fillna(False).astype(bool)

    done_rock_ids = ascents["gipfel_id"].unique() if not ascents.empty else []
    st.sidebar.write(f"✅ Begangene Felsen (distinct gipfel_id): {len(done_rock_ids)}")
    rocks["has_done_route"] = rocks["id"].isin(done_rock_ids)

    filter_status = st.sidebar.radio(
        "Anzeige der Felsen",
        ("Alle", "Begangene", "Unbegangene"),
        key="filter_status_radio"
    )
    if filter_status == "Begangene":
        rocks = rocks[rocks["has_done_route"] == True]
    elif filter_status == "Unbegangene":
        rocks = rocks[rocks["has_done_route"] == False]

    filter_has_star = st.sidebar.checkbox("⭐ Nur Felsen mit Stern anzeigen")
    if filter_has_star:
        rocks = rocks[rocks["rock_has_star"] == True]

    # --- Karte ---
    st.subheader("Interaktive Karte")
    filtered = rocks.dropna(subset=["latitude", "longitude"])
    st.sidebar.write(f"🗺️ Sichtbare Felsen nach Filter: {len(filtered)}")

    fixed_lat_center = 50.92
    fixed_lon_center = 14.15
    fixed_zoom_start = 12
    fixed_bounds = [[50.85, 14.00], [50.99, 14.30]]

    m = folium.Map(location=[fixed_lat_center, fixed_lon_center], zoom_start=fixed_zoom_start, tiles='CartoDB Positron')
    m.fit_bounds(fixed_bounds)

    for _, row in filtered.iterrows():
        anzahl = row.get("anzahl_routen", 0)
        if anzahl <= 5:
            größe = 0.0015
        elif anzahl <= 10:
            größe = 0.0022
        else:
            größe = 0.003

        if row.get("has_done_route", False):
            fill_color = PLOT_HIGHLIGHT_COLOR  # Cyan für begangene Felsen
        else:
            fill_color = PLOT_TEXT_COLOR       # Schwarz für unbegangene Felsen

        coords = make_triangle(row["latitude"], row["longitude"], größe)
        if coords:
            tooltip_content = f"""
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
                tooltip=folium.Tooltip(tooltip_content, sticky=True)
            ).add_to(m)

    st_folium(m, width=1400, height=600, key="folium_map")

    st.markdown("---")
    if st.button("Gefilterte Felsen anzeigen & herunterladen"):
        if not filtered.empty:
            st.subheader("Gefilterte Felsenliste")
            display_columns = ['name', 'gebiet', 'anzahl_routen', 'rock_has_star', 'has_done_route', 'latitude', 'longitude']
            display_df = filtered[display_columns].rename(columns={
                'name': 'Felsenname',
                'gebiet': 'Gebiet',
                'anzahl_routen': 'Anzahl Routen',
                'rock_has_star': 'Hat Stern',
                'has_done_route': 'Begangen'
            })
            st.dataframe(display_df, hide_index=True, use_container_width=True)
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Liste als CSV herunterladen",
                data=csv,
                file_name="gefilterte_felsen.csv",
                mime="text/csv",
            )
        else:
            st.info("Keine Felsen zum Anzeigen oder Herunterladen nach den angewendeten Filtern.")



if __name__ == "__main__":
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if url and key:
        supabase_client_direct = create_client(url, key)
        show_filter_map_page(supabase_client_direct)
    else:
        st.error("SUPABASE_URL oder SUPABASE_KEY nicht gesetzt. Kann nicht direkt ausgeführt werden.")
