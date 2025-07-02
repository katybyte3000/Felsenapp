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

# Globale Liste, um Debug-Nachrichten zu sammeln
debug_messages = []

def add_debug_message(message):
    """Fügt eine Debug-Nachricht zur globalen Liste hinzu."""
    debug_messages.append(message)

def display_debug_info():
    """Zeigt alle gesammelten Debug-Nachrichten an."""
    if debug_messages:
        st.subheader("Debugging Informationen")
        for msg in debug_messages:
            st.info(msg)
    else:
        st.info("Keine Debugging-Informationen gesammelt (oder alle Debug-Nachrichten sind deaktiviert).")

@st.cache_data
def fetch_data():
    """
    Holt alle notwendigen Daten aus Supabase:
    Sektoren, Rocks (mit verknüpftem Sektornamen), Routen und Begehungen.
    """
    try:
        add_debug_message("DEBUG FETCH_DATA: Start fetching data.")

        # 1. Sektoren laden
        sectors_response = supabase.table("sector").select("id, name").execute()
        sectors_df = pd.DataFrame(sectors_response.data)
        add_debug_message(f"DEBUG FETCH_DATA: Sektoren geladen: {len(sectors_df)}")
        if sectors_df.empty:
            st.warning("Keine Sektoren vorhanden.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        sectors_df['id'] = sectors_df['id'].astype(int)

        # 2. Felsen laden
        rocks_response = supabase.table("rocks").select("id, name, sector_id, latitude, longitude, hoehe").execute()
        rocks_df = pd.DataFrame(rocks_response.data)
        add_debug_message(f"DEBUG FETCH_DATA: Felsen geladen: {len(rocks_df)}")
        if rocks_df.empty:
            st.warning("Keine Felsen vorhanden.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        rocks_df['id'] = rocks_df['id'].astype(int)
        rocks_df['sector_id'] = rocks_df['sector_id'].astype(int)

        # Verknüpfen mit Sector-Name und Rock-ID erhalten
        rocks_df = rocks_df.merge(
            sectors_df,
            left_on="sector_id",
            right_on="id",
            how="left",
            suffixes=('_rock', '_sector')
        )
        rocks_df.rename(columns={
            "id_rock": "id",        # ID des Felsens wiederherstellen
            "name_rock": "name",    # Name des Felsens
            "name_sector": "gebiet" # Gebiet vom Sektor
        }, inplace=True)
        rocks_df.drop(columns=['id_sector'], errors='ignore', inplace=True)

        # 3. Routen laden
        routes_response = supabase.table("routes").select("id, rock_id, name, grade, number, stern").execute()
        routes_df = pd.DataFrame(routes_response.data)
        add_debug_message(f"DEBUG FETCH_DATA: Routen geladen: {len(routes_df)}")
        if routes_df.empty:
            st.warning("Keine Routen vorhanden.")
            return rocks_df, pd.DataFrame(), pd.DataFrame(), sectors_df
        routes_df['id'] = routes_df['id'].astype(int)
        routes_df['rock_id'] = routes_df['rock_id'].astype(int)
        routes_df['stern'] = routes_df.get('stern', False).astype(bool)

        # 4. Begehungen laden
        ascents_response = supabase.table("ascents").select("id, datum, gipfel_id, route_id, partnerin, stil, kommentar, bewertung").execute()
        ascents_df = pd.DataFrame(ascents_response.data)
        add_debug_message(f"DEBUG FETCH_DATA: Begehungen geladen: {len(ascents_df)}")
        if ascents_df.empty:
            st.info("Keine Begehungen vorhanden.")
            return rocks_df, routes_df, pd.DataFrame(), sectors_df

        # Optional: Umbenennen von 'id' zu 'ascent_id' zur Klarheit
        ascents_df.rename(columns={"id": "ascent_id"}, inplace=True)

        # Spaltentypen bereinigen
        ascents_df['gipfel_id'] = ascents_df['gipfel_id'].astype(int)
        if 'route_id' in ascents_df.columns:
            ascents_df['route_id'] = pd.to_numeric(ascents_df['route_id'], errors='coerce').fillna(0).astype(int)
        if 'bewertung' in ascents_df.columns:
            ascents_df['bewertung'] = pd.to_numeric(ascents_df['bewertung'], errors='coerce').fillna(0).astype(int)
        else:
            ascents_df['bewertung'] = 0

        st.success("Alle Daten erfolgreich geladen.")
        return rocks_df, routes_df, ascents_df, sectors_df

    except Exception as e:
        st.error(f"Fehler beim Laden der Daten aus Supabase: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


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

def app():
    st.set_page_config(layout="wide")
    st.title("Rockbook - Climbing App")

    rocks_df, routes_df, ascents_df, sectors_df = fetch_data()

    if rocks_df.empty or routes_df.empty:
        st.warning("Keine essentiellen Daten (Rocks oder Routen) verfügbar oder Fehler beim Laden. Bitte überprüfen Sie Ihre Supabase-Verbindung und Tabellen.")
        display_debug_info()
        st.stop()

    add_debug_message(f"DEBUG APP: Initial rocks_df rows: {len(rocks_df)}")
    add_debug_message(f"DEBUG APP: rocks_df columns: {rocks_df.columns.tolist()}")

    # --- Vorberechnungen für Rocks (basierend auf Routen und Begehungen) ---
    # 🔹 Berechne die Anzahl der Routen pro Rock
    if 'id' in routes_df.columns and 'rock_id' in routes_df.columns:
        route_counts = routes_df.groupby("rock_id").size().reset_index(name="anzahl_routen")
        rocks_df = rocks_df.merge(route_counts, left_on="id", right_on="rock_id", how="left", suffixes=('', '_route_count'))
        rocks_df["anzahl_routen"] = rocks_df["anzahl_routen"].fillna(0).astype(int)
        rocks_df.drop(columns=['rock_id_route_count'], errors='ignore', inplace=True)
    else:
        st.warning("Spalten 'id' oder 'rock_id' fehlen in 'routes_df', 'anzahl_routen' kann nicht berechnet werden.")
        rocks_df["anzahl_routen"] = 0

    # 🔹 Ermittle, ob Rock einen Stern hat (basiert auf routes.stern)
    if 'stern' in routes_df.columns and 'rock_id' in routes_df.columns:
        rock_has_star = routes_df.groupby('rock_id')['stern'].any().reset_index(name='rock_has_star')
        rocks_df = rocks_df.merge(rock_has_star, left_on='id', right_on='rock_id', how='left', suffixes=('', '_star'))
        rocks_df['rock_has_star'] = rocks_df['rock_has_star'].fillna(False).astype(bool)
        rocks_df.drop(columns=['rock_id_star'], errors='ignore', inplace=True)
        add_debug_message(f"DEBUG APP: rocks_df 'rock_has_star' unique values: {rocks_df['rock_has_star'].unique()}")
    else:
        rocks_df['rock_has_star'] = False

    # 🔹 Bestimme die höchste Bewertung pro Rock (basierend auf ascents.bewertung - ORIGINALNAME)
    # Beachte: 'bewertung' und 'gipfel_id' (ehemals rock_id in ascents) sind die originalen Namen
    if 'bewertung' in ascents_df.columns and 'route_id' in ascents_df.columns and 'id' in routes_df.columns and 'rock_id' in routes_df.columns:
        # Merge ascents with routes to get rock_id for ascents
        # HIER WICHTIG: ascents_df['gipfel_id'] ist der Rock/Peak, daher direkt verwenden
        # Wir brauchen die route_id, um zu sehen, welche ascents zu welcher Route gehören
        
        # Falls du eine Verknüpfung über route_id -> rock_id machen willst:
        ascents_with_rock_id = ascents_df.merge(routes_df[['id', 'rock_id']], left_on='route_id', right_on='id', how='left', suffixes=('_ascent', '_route'))
        
        # Den Fall behandeln, dass ascents.gipfel_id direkt der rock_id entspricht (falls so gedacht)
        # Wenn 'gipfel_id' direkt der 'rock_id' des Felsens ist, können wir das nutzen:
        # ascents_with_rock_id = ascents_df.rename(columns={'gipfel_id': 'rock_id_for_merge'}) # Rename for clarity if needed

        # Drop NaNs from rock_id after merge
        ascents_with_rock_id = ascents_with_rock_id.dropna(subset=['rock_id'])
        
        if not ascents_with_rock_id.empty:
            max_rating_per_rock = ascents_with_rock_id.groupby('rock_id')['bewertung'].max().reset_index(name='max_rating_per_rock')
            rocks_df = rocks_df.merge(max_rating_per_rock, left_on='id', right_on='rock_id', how='left', suffixes=('', '_rating'))
            rocks_df['max_rating_per_rock'] = rocks_df['max_rating_per_rock'].fillna(0).astype(int)
            rocks_df.drop(columns=['rock_id_rating'], errors='ignore', inplace=True)
        else:
            rocks_df['max_rating_per_rock'] = 0
    else:
        rocks_df['max_rating_per_rock'] = 0

    # 🔹 Bestimme für jeden ROCK, ob er mindestens EINE gemachte Route hat (has_done_route)
    # Hier verwenden wir die originalen Spaltennamen aus ascents_df ('route_id' und 'gipfel_id')
    if 'route_id' in ascents_df.columns and 'id' in routes_df.columns and 'rock_id' in routes_df.columns:
        done_route_ids = ascents_df['route_id'].unique().tolist()
        done_routes_info = routes_df[routes_df['id'].isin(done_route_ids)]
        done_rock_ids = done_routes_info['rock_id'].unique().tolist()
        rocks_df['has_done_route'] = rocks_df['id'].isin(done_rock_ids)
        add_debug_message(f"DEBUG APP: {rocks_df['has_done_route'].sum()} rocks have been climbed.")
    else:
        rocks_df['has_done_route'] = False


    # 🔹 Kommentar zum Rock mergen (basierend auf dem ersten Ascent für diesen Rock)
    # Hier verwenden wir die originalen Spaltennamen aus ascents_df ('kommentar', 'gipfel_id', 'datum')
    if 'kommentar' not in rocks_df.columns:
        rocks_df['kommentar'] = "" # Originalname wiederherstellen

    if not ascents_df.empty and 'kommentar' in ascents_df.columns and 'route_id' in ascents_df.columns and 'gipfel_id' in ascents_df.columns and 'datum' in ascents_df.columns:
        # Merge ascents with routes to get rock_id for each ascent comment
        ascents_routes_merged = ascents_df.merge(routes_df[['id', 'rock_id']], left_on='route_id', right_on='id', how='left', suffixes=('_ascent', '_route'))
        
        # Filter out rows where rock_id or comment are missing after merge
        ascents_routes_merged = ascents_routes_merged.dropna(subset=['rock_id', 'kommentar']) # 'kommentar' ist der Originalname

        if not ascents_routes_merged.empty:
            # Ensure 'datum' is datetime for sorting
            ascents_routes_merged['datum'] = pd.to_datetime(ascents_routes_merged['datum'], errors='coerce')
            ascents_routes_merged = ascents_routes_merged.sort_values(by='datum', ascending=True)
            
            # Get the unique rock_id and its first associated comment
            rock_comments = ascents_routes_merged.drop_duplicates(subset=['rock_id'], keep='first')[['rock_id', 'kommentar']] # 'kommentar_ascent' nach dem Merge
            rock_comments.rename(columns={'kommentar': 'merged_comment'}, inplace=True) # Umbenennen für klareren Merge

            # Merge these comments into the main rocks_df
            rocks_df = rocks_df.merge(rock_comments, left_on='id', right_on='rock_id', how='left', suffixes=('', '_merged'))
            
            # Use the new comment if available, otherwise keep original or empty string
            if 'merged_comment' in rocks_df.columns:
                rocks_df['kommentar'] = rocks_df['merged_comment'].fillna(rocks_df['kommentar']).astype(str)
                rocks_df.drop(columns=['merged_comment', 'rock_id_merged'], errors='ignore', inplace=True)
            else:
                rocks_df['kommentar'] = rocks_df['kommentar'].fillna("").astype(str)
        else:
            rocks_df['kommentar'] = rocks_df['kommentar'].fillna("").astype(str)
    else:
        rocks_df['kommentar'] = rocks_df['kommentar'].fillna("").astype(str)
    
    add_debug_message(f"DEBUG APP: rocks_df columns after all calculations: {rocks_df.columns.tolist()}")


    # 2. Filteroptionen
    st.sidebar.title("Filter Options")

    gebiet_filter_options = sorted(rocks_df['gebiet'].unique().tolist()) if 'gebiet' in rocks_df.columns and not rocks_df['gebiet'].empty else []
    if len(gebiet_filter_options) > 0:
        gebiet_filter = st.sidebar.selectbox('Select an area', options=['All Areas'] + gebiet_filter_options)
    else:
        st.sidebar.warning("No areas available for filtering.")
        gebiet_filter = 'All Areas'

    schwierigkeit_filter = st.sidebar.selectbox(
        'Select Rating',
        options=["All Ratings", "Easy", "Okay", "Hard"]
    )
    rating_filter_value = None
    if schwierigkeit_filter != "All Ratings":
        rating_filter_value = {
            "Easy": 1,
            "Okay": 2,
            "Hard": 3
        }[schwierigkeit_filter]

    sternchen_filter = st.sidebar.radio(
        "Select routes with or without a star",
        options=["All", "Has Star", "No Star"]
    )
    if sternchen_filter == "Has Star":
        sternchen_filter_value = True
    elif sternchen_filter == "No Star":
        sternchen_filter_value = False
    else:
        sternchen_filter_value = None

    if 'hoehe' in rocks_df.columns and pd.api.types.is_numeric_dtype(rocks_df['hoehe']):
        min_hoehe = int(rocks_df['hoehe'].min()) if not rocks_df['hoehe'].empty and pd.notna(rocks_df['hoehe'].min()) else 0
        max_hoehe = int(rocks_df['hoehe'].max()) if not rocks_df['hoehe'].empty and pd.notna(rocks_df['hoehe'].max()) else 3000
        hoehe_filter = st.sidebar.slider('Select maximum rock height in meters', min_value=min_hoehe, max_value=max_hoehe, step=10, value=max_hoehe)
    else:
        st.sidebar.warning("Height filter not available as 'hoehe' column is missing or not numeric.")
        hoehe_filter = None

    gemacht_filter = st.sidebar.checkbox('Show climbed routes')

    # 3. Apply Filters - Startet mit rocks_df
    add_debug_message(f"DEBUG FILTER START: filtered_rocks rows (before any filters): {len(rocks_df)}")
    filtered_rocks = rocks_df.copy()

    # Gebiet Filter
    add_debug_message(f"DEBUG FILTER GEBIET (before): rows: {len(filtered_rocks)}")
    if gebiet_filter != 'All Areas':
        if 'gebiet' in filtered_rocks.columns:
            filtered_rocks = filtered_rocks[filtered_rocks['gebiet'] == gebiet_filter]
        else:
            st.warning("Column 'gebiet' missing, area filter ignored.")
    add_debug_message(f"DEBUG FILTER GEBIET (after): rows: {len(filtered_rocks)}")

    # Rating Filter
    add_debug_message(f"DEBUG FILTER RATING (before): rows: {len(filtered_rocks)}")
    if rating_filter_value is not None:
        if 'max_rating_per_rock' in filtered_rocks.columns:
            filtered_rocks = filtered_rocks[filtered_rocks['max_rating_per_rock'] == rating_filter_value]
        else:
            st.warning("Column 'max_rating_per_rock' not found, rating filter ignored.")
    add_debug_message(f"DEBUG FILTER RATING (after): rows: {len(filtered_rocks)}")

    # Star Filter
    add_debug_message(f"DEBUG FILTER STAR (before): rows: {len(filtered_rocks)}")
    if sternchen_filter_value is not None:
        if 'rock_has_star' in filtered_rocks.columns:
            filtered_rocks = filtered_rocks[filtered_rocks['rock_has_star'] == sternchen_filter_value]
            add_debug_message(f"DEBUG AFTER 'rock_has_star' filter: rows: {len(filtered_rocks)}")
        else:
            st.warning("Column 'rock_has_star' not found, star filter ignored.")
    add_debug_message(f"DEBUG FILTER STAR (after): rows: {len(filtered_rocks)}")

    # Height Filter
    add_debug_message(f"DEBUG FILTER HEIGHT (before): rows: {len(filtered_rocks)}")
    if hoehe_filter is not None and 'hoehe' in filtered_rocks.columns:
        filtered_rocks = filtered_rocks[pd.to_numeric(filtered_rocks['hoehe'], errors='coerce').fillna(0) <= hoehe_filter]
    add_debug_message(f"DEBUG FILTER HEIGHT (after): rows: {len(filtered_rocks)}")

    # 'Done' Filter
    add_debug_message(f"DEBUG FILTER DONE (before): rows: {len(filtered_rocks)}")
    if gemacht_filter:
        if 'has_done_route' in filtered_rocks.columns:
            filtered_rocks = filtered_rocks[filtered_rocks['has_done_route'] == True]
            add_debug_message(f"Debugging: {len(filtered_rocks)} rocks contain done routes after filter.")
        else:
            st.warning("Column 'has_done_route' missing. 'Done' filter ignored.")
    add_debug_message(f"DEBUG FILTER DONE (after): rows: {len(filtered_rocks)}")
    
    # Debugging nach allen Filtern
    add_debug_message(f"DEBUG AFTER ALL FILTERS (final count): filtered_rocks rows: {len(filtered_rocks)}")
    if 'rock_has_star' in filtered_rocks.columns:
        add_debug_message(f"DEBUG AFTER ALL FILTERS: filtered_rocks 'rock_has_star' unique values: {filtered_rocks['rock_has_star'].unique()}")
    if 'has_done_route' in filtered_rocks.columns:
        add_debug_message(f"DEBUG AFTER ALL FILTERS: filtered_rocks 'has_done_route' unique values: {filtered_rocks['has_done_route'].unique()}")


    # **Überprüfung und Bereinigung von NaN-Werten für Kartenplotting**
    initial_rows_for_plotting_check = len(filtered_rocks)
    
    required_cols_for_plot = ['latitude', 'longitude', 'hoehe', 'name', 'gebiet', 'anzahl_routen']
    if 'rock_has_star' in filtered_rocks.columns:
        required_cols_for_plot.append('rock_has_star')
    if 'has_done_route' in filtered_rocks.columns:
        required_cols_for_plot.append('has_done_route')
    if 'kommentar' in filtered_rocks.columns: # Hier wieder 'kommentar'
        required_cols_for_plot.append('kommentar')

    cols_to_check = [col for col in required_cols_for_plot if col in filtered_rocks.columns]
    
    if cols_to_check:
        filtered_rocks = filtered_rocks.dropna(subset=cols_to_check)
        if len(filtered_rocks) < initial_rows_for_plotting_check:
            st.warning(f"Es wurden {initial_rows_for_plotting_check - len(filtered_rocks)} Rocks mit fehlenden Daten (Koordinaten, Höhe etc.) für die Kartenanzeige entfernt.")
    else:
        st.warning("Wichtige Spalten (latitude, longitude, hoehe) für die Kartenanzeige fehlen in 'filtered_rocks'.")
        filtered_rocks = pd.DataFrame() 

    add_debug_message(f"DEBUG FINAL PLOTTING COUNT: rows after NaN drop for map: {len(filtered_rocks)}")

    # 5. Ausgabe der gefilterten Rockpunkte als Liste
    st.subheader("Gefilterte Rocks")
    if not filtered_rocks.empty:
        display_columns = ['name', 'gebiet', 'hoehe', 'anzahl_routen']
        if 'max_rating_per_rock' in filtered_rocks.columns:
            display_columns.append('max_rating_per_rock')
        if 'rock_has_star' in filtered_rocks.columns:
            display_columns.append('rock_has_star')
        if 'has_done_route' in filtered_rocks.columns:
            display_columns.append('has_done_route')
        if 'kommentar' in filtered_rocks.columns: # Hier wieder 'kommentar'
            display_columns.append('kommentar')

        actual_display_columns = [col for col in display_columns if col in filtered_rocks.columns]
        
        st.dataframe(filtered_rocks[actual_display_columns])
        st.write(f"Gesamtanzahl der angezeigten Rocks nach Filtern und Bereinigung: {len(filtered_rocks)}")
    else:
        st.info("Keine Rocks gefunden, die den aktuellen Filtern entsprechen oder alle notwendigen Daten für die Anzeige haben.")

    # 6. Kartenmittelpunkt berechnen
    st.subheader("Interaktive Karte")
    if not filtered_rocks.empty and 'latitude' in filtered_rocks.columns and 'longitude' in filtered_rocks.columns:
        filtered_rocks['latitude'] = pd.to_numeric(filtered_rocks['latitude'], errors='coerce')
        filtered_rocks['longitude'] = pd.to_numeric(filtered_rocks['longitude'], errors='coerce')
        filtered_rocks_for_map = filtered_rocks.dropna(subset=['latitude', 'longitude'])

        if not filtered_rocks_for_map.empty:
            lat_center = filtered_rocks_for_map["latitude"].mean()
            lon_center = filtered_rocks_for_map["longitude"].mean()
        else:
            st.info("No rocks with valid coordinates available to center the map and display triangles.")
            display_debug_info() 
            return 
    else:
        st.info("No rocks available to center the map and display triangles (missing latitude/longitude columns or data).")
        display_debug_info() 
        return 

    # 7. Folium-Karte erstellen
    m = folium.Map(
        location=[lat_center, lon_center],
        zoom_start=11,
        tiles='CartoDB Positron',
        attr='&copy; <a href="https://carto.com/attributions">CartoDB</a>'
    )

    # 8. Dreiecke als Polygone einfügen (Größe nach Höhe)
    drawn_triangles_count = 0
    for index, row in filtered_rocks_for_map.iterrows(): 
        if not all(col in row.index and pd.notna(row[col]) for col in ['latitude', 'longitude', 'hoehe', 'anzahl_routen', 'name', 'gebiet']):
            add_debug_message(f"Skipping row {index} due to missing critical columns or NaN: {row.to_dict()}")
            continue 
        
        hoehe_val = pd.to_numeric(row["hoehe"], errors='coerce')
        if pd.isna(hoehe_val) or hoehe_val < 0: 
            add_debug_message(f"Skipping row {index} due to invalid height: {row['hoehe']}")
            continue

        größe = 0.0012 + (hoehe_val * 0.00011)
        if größe <= 0: 
            add_debug_message(f"Skipping row {index} due to invalid calculated size: {größe}")
            continue

        fill_color = "red" 
        
        if row.get('rock_has_star', False):
            fill_color = "purple"
        
        if row.get('has_done_route', False):
            fill_color = "black"

        coords = make_triangle(row["latitude"], row["longitude"], größe)
        if coords: 
            tooltip_text = f"""
            <b>{row['name']}</b><br>
            Height: {int(hoehe_val)} m<br>
            Routes: {int(row['anzahl_routen'])}<br>
            Area: {row['gebiet']}
            """
            if 'rock_has_star' in row:
                tooltip_text += f"<br>Star: {'⭐' if row['rock_has_star'] else 'No'}"
            if 'has_done_route' in row:
                tooltip_text += f"<br>Climbed: {'✅' if row['has_done_route'] else '❌'}"
            
            if 'kommentar' in row and row['kommentar']: # Hier wieder 'kommentar'
                tooltip_text += f"<br>Comment: {row['kommentar']}"


            folium.Polygon(
                locations=coords,
                color=None,
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.89,
                tooltip=folium.Tooltip(tooltip_text, sticky=True)
            ).add_to(m)
            drawn_triangles_count += 1
        else:
            add_debug_message(f"Skipping row {index} - could not create triangle coordinates: lat={row['latitude']}, lon={row['longitude']}")
            
    add_debug_message(f"Number of triangles drawn on the map: {drawn_triangles_count}")

    st_data = st_folium(m, width=1400, height=600)

    # Neuer Abschnitt für Debugging-Informationen am Ende der Seite
    display_debug_info()


if __name__ == "__main__":
    app()