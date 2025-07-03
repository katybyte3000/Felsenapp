import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from supabase import create_client, Client # create_client wird hier nicht mehr direkt verwendet, aber der Import bleibt für den Typ-Hint
import os
from dotenv import load_dotenv # load_dotenv wird hier nicht mehr direkt verwendet
import math


# --- FARBKONZEPT KONSTANTEN (Müssen mit app.py übereinstimmen) ---
BG_COLOR = "#FFEF16"        # Dein lebendiges Gelb
HIGHLIGHT_COLOR = "#006D77" # Petrol
POSITIVE_COLOR = "#3BB273"  # Grün
NEGATIVE_COLOR = "#8E44AD"  # Lila
SECONDARY_COLOR = "#83C5BE" # Helles Petrol
TEXT_COLOR = "#1D1D1D"      # Dunkelgrau


def make_triangle(lat, lon, size=0.001):
    """
    Erstellt die Koordinaten für ein Dreieck, das als Marker auf der Karte verwendet wird.
    """
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

# @st.cache_data # DIESER DECORATOR WURDE ENTFERNT
def fetch_data(_supabase_client: Client, user_id: str):
    """
    Holt alle notwendigen Daten (Sektoren, Felsen, Routen, Begehungen) aus Supabase.
    Verwendet Paginierung für Routen, um mehr als 1000 Einträge zu laden.
    """
    try:
        sectors = pd.DataFrame(_supabase_client.table("sector").select("id, name").execute().data)
        sectors['id'] = sectors['id'].astype(int)

        rocks = pd.DataFrame(_supabase_client.table("rocks").select("id, name, sector_id, latitude, longitude, hoehe").range(0, 5000).execute().data)
        rocks['id'] = rocks['id'].astype(int)
        rocks['sector_id'] = rocks['sector_id'].astype(int)

        # Mergen der Sektornamen zu den Felsen
        rocks = rocks.merge(sectors, left_on="sector_id", right_on="id", suffixes=("_rock", "_sector"))
        rocks.rename(columns={"name_sector": "gebiet", "name_rock": "name", "id_rock": "id"}, inplace=True)
        rocks.drop(columns=["id_sector"], errors='ignore', inplace=True)

        # Alle rock_ids und grades aus routes laden (mehr als 1000)
        def fetch_all_routes_column_internal():
            full_data = []
            step = 1000
            # Annahme: Max 25000 Routen. Anpassen, falls mehr benötigt werden.
            for start in range(0, 25000, step):
                end = start + step - 1
                chunk = _supabase_client.table("routes").select("rock_id, grade, name, number").range(start, end).execute().data
                if not chunk:
                    break # Keine weiteren Daten
                full_data.extend(chunk)
            return pd.DataFrame(full_data)

        routes_full_data = fetch_all_routes_column_internal()
        routes_full_data['rock_id'] = routes_full_data['rock_id'].astype(int)
        routes_full_data['grade'] = pd.to_numeric(routes_full_data['grade'], errors='coerce')

        # Routen mit Stern-Informationen (für die Karte)
        routes_for_stars = pd.DataFrame(_supabase_client.table("routes").select("id, rock_id, stern").range(0, 5000).execute().data)
        routes_for_stars['id'] = routes_for_stars['id'].astype(int)
        routes_for_stars['rock_id'] = routes_for_stars['rock_id'].astype(int)
        routes_for_stars['stern'] = routes_for_stars.get('stern', False).astype(bool)

        # Begehungen des angemeldeten Benutzers
        if user_id:
            ascents = pd.DataFrame(_supabase_client.table("ascents").select("id, gipfel_id, route_id, bewertung, kommentar").eq("user_id", user_id).execute().data)
        else:
            ascents = pd.DataFrame() # Leerer DataFrame, wenn kein Benutzer eingeloggt ist

        ascents.rename(columns={"id": "ascent_id"}, inplace=True)
        ascents['gipfel_id'] = pd.to_numeric(ascents['gipfel_id'], errors='coerce').fillna(0).astype(int)
        ascents['route_id'] = pd.to_numeric(ascents['route_id'], errors='coerce').fillna(0).astype(int)
        ascents['bewertung'] = pd.to_numeric(ascents['bewertung'], errors='coerce').fillna(0).astype(int)

        return rocks, routes_for_stars, ascents, routes_full_data # Rückgabe von routes_full_data
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# Die show_gipfel_detail_page Funktion wird nicht mehr direkt aufgerufen,
# da wir die Klickfunktion deaktivieren. Sie kann aber für zukünftige Erweiterungen
# oder andere Seiten nützlich sein, daher lasse ich sie hier.
def show_gipfel_detail_page(gipfel_id: int, _supabase_client: Client, user_id: str):
    """
    Zeigt die Detailseite für einen ausgewählten Gipfel an.
    """
    st.markdown('<div class="headline-fonts">Gipfel Details</div>', unsafe_allow_html=True)

    # Button zum Zurückkehren zur Karte
    if st.button("⬅️ Zurück zur Karte"):
        st.session_state.selected_gipfel_id = None
        st.rerun()

    # Daten für den spezifischen Gipfel abrufen
    rocks, routes_for_stars, ascents, routes_full_data = fetch_data(_supabase_client, user_id)
    
    selected_rock = rocks[rocks['id'] == gipfel_id]

    if selected_rock.empty:
        st.error(f"Gipfel mit ID {gipfel_id} nicht gefunden.")
        return

    rock_info = selected_rock.iloc[0]
    st.subheader(f"{rock_info['name']}")
    st.write(f"**Gebiet:** {rock_info['gebiet']}")
    st.write(f"**Höhe:** {rock_info.get('hoehe', 'N/A')} m") # 'hoehe' aus rocks.select hinzugefügt
    st.write(f"**Koordinaten:** {rock_info['latitude']:.4f}, {rock_info['longitude']:.4f}")

    st.markdown("---")
    st.markdown(f'<p style="font-family: \'Noto Sans\', sans-serif; font-weight: 700; color:{TEXT_COLOR};">Routen an diesem Gipfel</p>', unsafe_allow_html=True)

    # Routen für diesen Gipfel filtern
    gipfel_routes = routes_full_data[routes_full_data['rock_id'] == gipfel_id].copy()

    if not gipfel_routes.empty:
        # Mergen der Begehungsdaten mit den Routen, um zu sehen, welche Routen begangen wurden
        gipfel_routes['begangen'] = gipfel_routes['id'].isin(ascents['route_id'])
        
        # Sortieren nach Schwierigkeitsgrad
        gipfel_routes = gipfel_routes.sort_values(by='grade', ascending=True)

        # Anzeige der Routen in einer Tabelle
        st.dataframe(
            gipfel_routes[['name', 'number', 'grade', 'begangen']].rename(
                columns={'name': 'Routenname', 'number': 'Nummer', 'grade': 'Schwierigkeit', 'begangen': 'Begangen'}),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Für diesen Gipfel wurden keine Routen gefunden.")

    st.markdown("---")
    st.markdown(f'<p style="font-family: \'Noto Sans\', sans-serif; font-weight: 700; color:{TEXT_COLOR};">Ihre Begehungen an diesem Gipfel</p>', unsafe_allow_html=True)
    
    user_ascents_on_gipfel = ascents[ascents['gipfel_id'] == gipfel_id].copy()

    if not user_ascents_on_gipfel.empty:
        # Mergen mit Routennamen und Schwierigkeit
        user_ascents_on_gipfel = user_ascents_on_gipfel.merge(
            routes_full_data[['id', 'name', 'number', 'grade']],
            left_on='route_id',
            right_on='id',
            how='left',
            suffixes=('_ascent', '_route')
        )
        st.dataframe(
            user_ascents_on_gipfel[['name_route', 'number', 'grade', 'bewertung', 'kommentar']].rename(
                columns={'name_route': 'Route', 'number': 'Nummer', 'grade': 'Schwierigkeit', 'bewertung': 'Ihre Bewertung', 'kommentar': 'Ihr Kommentar'}),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Sie haben diesen Gipfel noch nicht bestiegen.")

    # Button zum Zurückkehren zur Karte (optional, da oben schon vorhanden)
    if st.button("Zurück zur Karte", key="back_to_map_bottom"):
        st.session_state.selected_gipfel_id = None
        st.rerun()


def show_filter_map_page(supabase_client: Client): # supabase_client als Argument
    """
    Zeigt die interaktive Filterkarte an.
    Dies ist die Hauptfunktion für die 'Filterkarte'-Seite.
    """
    # Verwende die headline-fonts Klasse für den Titel, um Oswald-Schriftart zu nutzen
    st.markdown('<div class="headline-fonts">Gipfelkarte: Felsen finden</div>', unsafe_allow_html=True)

    # Übergeben Sie den supabase_client und die user_id an fetch_data
    rocks, routes_for_stars, ascents, routes_full_data = fetch_data(supabase_client, st.session_state.get("user_id"))

    if rocks.empty:
        st.warning("Keine Felsen zum Anzeigen verfügbar. Überprüfen Sie Ihre Datenquelle.")
        return

    st.sidebar.title("Filter")

    st.sidebar.write(f"🪨 Geladene Felsen: {len(rocks)}")

    # Filter nach Gebiet
    gebiete = sorted(rocks["gebiet"].dropna().unique())
    selected_gebiet = st.sidebar.selectbox("Gebiet auswählen", ["Alle"] + gebiete)

    # Filter nach Schwierigkeitsgrad
    grade_filter_enabled = st.sidebar.checkbox("Nach Schwierigkeitsgrad filtern")
    if grade_filter_enabled:
        grade_range = st.sidebar.slider("Schwierigkeitsgradbereich (1-12)", 1, 12, (1, 12))
        grad_filter = routes_full_data[routes_full_data['grade'].between(grade_range[0], grade_range[1])]
        allowed_rock_ids = grad_filter['rock_id'].unique()
        rocks = rocks[rocks['id'].isin(allowed_rock_ids)]

    # Anwenden der Gebietsfilter
    if selected_gebiet != "Alle":
        rocks = rocks[rocks["gebiet"] == selected_gebiet]

    # Routenanzahl zu den Felsen mergen
    route_counts = routes_full_data.groupby("rock_id").size().reset_index(name="anzahl_routen")
    rocks = rocks.merge(route_counts, left_on="id", right_on="rock_id", how="left")
    rocks["anzahl_routen"] = rocks["anzahl_routen"].fillna(0).astype(int)

    # Stern-Informationen zu den Felsen mergen
    star_rocks = routes_for_stars.groupby("rock_id")["stern"].any().reset_index().rename(columns={"stern": "rock_has_star"})
    rocks = rocks.merge(star_rocks, left_on="id", right_on="rock_id", how="left")
    rocks["rock_has_star"] = rocks["rock_has_star"].fillna(False).astype(bool)

    # Begangene Felsen identifizieren
    done_rock_ids = ascents["gipfel_id"].unique() if not ascents.empty else []
    st.sidebar.write(f"✅ Begangene Felsen (distinct gipfel_id): {len(done_rock_ids)}")
    rocks["has_done_route"] = rocks["id"].isin(done_rock_ids)

    # Filter für begangene/unbegangene Felsen mit Radio-Buttons
    filter_status = st.sidebar.radio(
        "Anzeige der Felsen",
        ("Alle", "Begangene", "Unbegangene"),
        key="filter_status_radio"
    )

    if filter_status == "Begangene":
        rocks = rocks[rocks["has_done_route"] == True]
    elif filter_status == "Unbegangene":
        rocks = rocks[rocks["has_done_route"] == False]
    # Wenn "Alle" ausgewählt ist, wird kein zusätzlicher Filter angewendet

    # Filter "Hat Stern"
    filter_has_star = st.sidebar.checkbox("⭐ Nur Felsen mit Stern anzeigen")
    if filter_has_star:
        rocks = rocks[rocks["rock_has_star"] == True]

    st.subheader("Interaktive Karte")
    filtered = rocks.dropna(subset=["latitude", "longitude"])

    st.sidebar.write(f"🗺️ Sichtbare Felsen nach Filter: {len(filtered)}")

    # Feste Standard-Koordinaten und Bounding Box für die Sächsische Schweiz
    fixed_lat_center = 50.92
    fixed_lon_center = 14.15
    fixed_zoom_start = 12

    # Feste Bounding Box für die Sächsische Schweiz
    fixed_bounds = [[50.85, 14.00], [50.99, 14.30]]

    m = folium.Map(location=[fixed_lat_center, fixed_lon_center], zoom_start=fixed_zoom_start, tiles='CartoDB Positron')
    m.fit_bounds(fixed_bounds) # Passt den Zoom an die feste Bounding Box an

    # Marker für jeden Felsen hinzufügen
    for _, row in filtered.iterrows():
        anzahl = row.get("anzahl_routen", 0)
        
        # Größe des Dreiecks basierend auf Routenanzahl
        if anzahl <= 5:
            größe = 0.0015
        elif anzahl <= 10:
            größe = 0.0022
        else:
            größe = 0.003

        # Farbe des Dreiecks basierend auf Status
        if row.get("has_done_route", False):
            fill_color = HIGHLIGHT_COLOR # Petrol für begangene Felsen
        else:
            fill_color = TEXT_COLOR # Schwarz für unbegangene Felsen

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
                color=None, # Keine Umrandung
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.89,
                tooltip=folium.Tooltip(tooltip_content, sticky=True)
            ).add_to(m)
            

    # Karte in Streamlit anzeigen.
    st_folium(m, width=1400, height=600, key="folium_map")

    st.markdown("---")
    # Button zum Anzeigen und Herunterladen der gefilterten Felsen
    if st.button("Gefilterte Felsen anzeigen & herunterladen"):
        if not filtered.empty:
            st.subheader("Gefilterte Felsenliste")
            # Auswahl der relevanten Spalten für die Anzeige
            display_columns = ['name', 'gebiet', 'anzahl_routen', 'rock_has_star', 'has_done_route', 'latitude', 'longitude']
            
            # Umbenennen der Spalten für eine bessere Lesbarkeit
            display_df = filtered[display_columns].rename(columns={
                'name': 'Felsenname',
                'gebiet': 'Gebiet',
                'anzahl_routen': 'Anzahl Routen',
                'rock_has_star': 'Hat Stern',
                'has_done_route': 'Begangen'
            })
            
            # Anzeige der Tabelle
            st.dataframe(display_df, hide_index=True, use_container_width=True)

            # Download-Button für die CSV-Datei
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Liste als CSV herunterladen",
                data=csv,
                file_name="gefilterte_felsen.csv",
                mime="text/csv",
            )
        else:
            st.info("Keine Felsen zum Anzeigen oder Herunterladen nach den angewendeten Filtern.")


# Wenn diese Datei direkt ausgeführt wird (was in Streamlit-Seiten normalerweise nicht der Fall ist,
# da sie über die Haupt-App aufgerufen werden), kann dies nützlich sein.
if __name__ == "__main__":
    # Wenn filtermap.py direkt ausgeführt wird, muss der Client hier erstellt werden.
    # Im normalen App-Flow wird dieser Block nicht ausgeführt.
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if url and key:
        supabase_client_direct = create_client(url, key)
        show_filter_map_page(supabase_client_direct)
    else:
        st.error("SUPABASE_URL oder SUPABASE_KEY nicht gesetzt. Kann nicht direkt ausgeführt werden.")
