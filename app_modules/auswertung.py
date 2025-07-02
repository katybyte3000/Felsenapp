import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px

# .env laden – robust für Seiten im "app_modules/"-Ordner
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)

# Supabase-Verbindung
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Hilfsfunktionen ---
def apply_plotly_background(fig):
    """Setzt den Hintergrund für Plotly-Diagramme."""
    fig.update_layout(
        paper_bgcolor="#f0e68c",
        plot_bgcolor="#f0e68c"
    )
    return fig

@st.cache_data
def fetch_data(user_id):
    """
    Holt Daten aus Supabase, gefiltert nach der user_id.
    rocks und sectors sind globale Daten, ascents sind user-spezifisch.
    """
    rocks = pd.DataFrame(supabase.table("rocks").select("id, sector_id").range(0, 5000).execute().data)
    sectors = pd.DataFrame(supabase.table("sector").select("id, name").execute().data)

    if user_id:
        ascents_data = supabase.table("ascents").select("route_id, gipfel_id, stil, datum, partnerin, user_id").eq("user_id", user_id).execute().data
        ascents = pd.DataFrame(ascents_data)
    else:
        ascents = pd.DataFrame() # Leerer DataFrame, wenn kein User eingeloggt ist

    return rocks, ascents, sectors

# --- Hauptfunktion für die Statistikseite ---
def main_app_auswertung():
    """
    Zeigt die Statistikseite der Anwendung an.
    Wird von app.py aufgerufen, wenn der Benutzer eingeloggt ist.
    """
    st.title("📊 Gipfel Statistik")

    # Sicherstellen, dass user_id im Session State vorhanden ist
    if st.session_state.user_id is None:
        st.error("Fehler: Kein Benutzer eingeloggt. Bitte melden Sie sich über die Hauptseite an, um Ihre Statistiken zu sehen.")
        return

    # Daten für den eingeloggten Benutzer abrufen
    rocks, ascents, sectors = fetch_data(st.session_state.user_id)

    # Wenn keine Begehungen für den User vorhanden sind
    if ascents.empty:
        st.info("Sie haben noch keine Begehungen eingetragen. Tragen Sie Ihre erste Begehung auf der Seite 'Begehung hinzufügen' ein!")
        return

    # --- Allgemeine Berechnungen ---
    total_rocks = len(rocks)
    unique_done_rocks = ascents['gipfel_id'].dropna().astype(int).unique()
    num_done_rocks = len(unique_done_rocks)
    # Definition von num_done_routes
    unique_done_routes = ascents['route_id'].dropna().astype(int).unique() 
    num_done_routes = len(unique_done_routes)
    
    percent_done = round((num_done_rocks / total_rocks) * 100, 1) if total_rocks > 0 else 0

    st.subheader("🔍 Überblick")

    ascents['datum'] = pd.to_datetime(ascents['datum'], errors='coerce')
    current_year = pd.Timestamp.now().year

    col_d1, col_d2, col_stats = st.columns([1, 2, 2])

    # === DONUT Fortschritt Gesamt (kleiner, schick) ===
    with col_d1:
        donut_percent = percent_done

        fig_donut1 = go.Figure(go.Pie(
            values=[donut_percent, 100 - donut_percent],
            hole=0.7,
            marker_colors=["#8CF0B4", "#e0e0e0"],
            textinfo='none',
            sort=False
        ))
        fig_donut1.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=250,
            annotations=[dict(
                text=f"<b>{donut_percent:.0f}%</b>",
                x=0.5, y=0.5,
                font_size=36,
                showarrow=False
            )]
        )

        st.markdown("##### Geschafft", unsafe_allow_html=True)
        st.plotly_chart(apply_plotly_background(fig_donut1), use_container_width=True)

    # === BALKEN: Gipfel pro Jahr animiert, breit, große Zahlen ===
    with col_d2:
        last_years = [current_year - 2, current_year - 1, current_year]
        yearly_gipfel = []

        for y in last_years:
            count = ascents[ascents['datum'].dt.year == y]['gipfel_id'].dropna().astype(int).nunique()
            yearly_gipfel.append(count)

        df_years = pd.DataFrame({
            'Jahr': last_years,
            'Gipfel': yearly_gipfel
        })

        fig_years = go.Figure()

        for i, row in df_years.iterrows():
            fig_years.add_trace(go.Bar(
                y=[str(row['Jahr'])],
                x=[row['Gipfel']],
                orientation='h',
                marker_color='#8CF0B4',
                text=[f"{row['Gipfel']}  "],
                textposition='inside',
                insidetextfont=dict(
                    family='Onest',
                    size=24,
                    color='black'
                ),
                hovertemplate=f"<b>{row['Jahr']}</b><br>Gipfel: {row['Gipfel']}<extra></extra>"
            ))

        fig_years.update_layout(
            title="Gipfel pro Jahr",
            xaxis_title="",
            yaxis_title="",
            height=300,
            margin=dict(t=40, b=20),
            showlegend=False,
            transition=dict(duration=500)
        )

        st.plotly_chart(apply_plotly_background(fig_years), use_container_width=True)

    # === STATISTIK-KÄSTCHEN stilisiert ===
    with col_stats:
        top_partner = ascents['partnerin'].dropna().mode()
        top_partner_name = top_partner.iloc[0].upper() if not top_partner.empty else "KEINE DATEN"

        if not ascents['gipfel_id'].dropna().empty:
            top_berg_id = ascents['gipfel_id'].dropna().astype(int).mode().iloc[0]
            gipfel_info = rocks[rocks['id'] == top_berg_id]

            if not gipfel_info.empty:
                sector_id = gipfel_info.iloc[0]['sector_id']
                sector_info = sectors[sectors['id'] == sector_id]
                berg_name_str = sector_info.iloc[0]['name'] if not sector_info.empty else f"Gipfel #{top_berg_id}"
            else:
                berg_name_str = f"Gipfel #{top_berg_id}"
        else:
            berg_name_str = "Keine Daten"

        total_routes_done = len(ascents)

        st.markdown("""
        <div style='line-height:1.2'>
            <span style='font-size:14px; color:#444'>Top Partner*in</span><br>
            <span style='font-size:32px; font-weight:600;'>""" + top_partner_name + """</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='line-height:1.2; margin-top:1em'>
            <span style='font-size:14px; color:#444'>Meistbegangener Gipfel</span><br>
            <span style='font-size:28px; font-weight:600;'>""" + berg_name_str + """</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='line-height:1.2; margin-top:1em'>
            <span style='font-size:14px; color:#444'>Begangene Begehungen</span><br>
            <span style='font-size:36px; font-weight:700;'>""" + str(total_routes_done) + """</span>
        </div>
        """, unsafe_allow_html=True)


    col1, col2, col3 = st.columns(3) # Die Definition von col1, col2, col3 ist hier!

    with col1:
        st.metric("🧗 Begangene Routen", f"{num_done_routes}")

    with col2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percent_done,
            number={"suffix": "%"},
            title={"text": "Erreichte Felsen (in %)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "green"},
                'steps': [{'range': [0, 100], 'color': "#e0e0e0"}]
            }
        ))
        st.plotly_chart(apply_plotly_background(fig), use_container_width=True)

    with col3:
        if 'stil' in ascents.columns:
            stil_counts = ascents['stil'].value_counts()
            fig_pie = go.Figure(data=[go.Pie(
                labels=stil_counts.index,
                values=stil_counts.values,
                hole=0.4,
                textinfo='label+percent',
                marker=dict(colors=['#4CAF50', '#FFC107', '#2196F3', '#FF5722'])
            )])
            fig_pie.update_layout(title_text="Verteilung der Stile")
            st.plotly_chart(apply_plotly_background(fig_pie), use_container_width=True)

    st.subheader("🗺️ Übersicht pro Gebiet")

    rocks['done'] = rocks['id'].isin(unique_done_rocks)
    sector_stats = rocks.groupby('sector_id')['done'].agg(['sum', 'count']).reset_index()
    sector_stats = sector_stats.merge(sectors, left_on='sector_id', right_on='id', how='left')
    sector_stats.rename(columns={'sum': 'begangen', 'count': 'gesamt', 'name': 'Gebiet'}, inplace=True)
    sector_stats = sector_stats.sort_values("gesamt", ascending=True)

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        y=sector_stats['Gebiet'],
        x=sector_stats['gesamt'],
        name='Gesamt',
        orientation='h',
        marker_color='#e0e0e0'
    ))
    fig_bar.add_trace(go.Bar(
        y=sector_stats['Gebiet'],
        x=sector_stats['begangen'],
        name='Begangen',
        orientation='h',
        marker_color='green'
    ))
    fig_bar.update_layout(
        barmode='overlay',
        title='Felsen pro Gebiet (grün = begangen)',
        xaxis_title='Anzahl Felsen',
        yaxis_title='',
        height=600,
        showlegend=False
    )
    st.plotly_chart(apply_plotly_background(fig_bar), use_container_width=True)

    st.subheader("📈 Entwicklung der Begehungen nach Stil")
    if 'datum' in ascents.columns and 'stil' in ascents.columns:
        # Sicherstellen, dass 'stil' gültige Werte hat
        valid_styles = ["Vorstieg", "Nachstieg", "Solo"]
        
        fig_time_styles = go.Figure()
        
        for stil_name in valid_styles:
            # Filter nach Stil und gruppieren nach Monat
            style_ascents = ascents[ascents['stil'] == stil_name].dropna(subset=['datum'])
            ascents_by_month_style = style_ascents.groupby(pd.Grouper(key='datum', freq='M')).size().reset_index(name='Anzahl')
            
            if not ascents_by_month_style.empty:
                fig_time_styles.add_trace(go.Scatter(
                    x=ascents_by_month_style['datum'],
                    y=ascents_by_month_style['Anzahl'],
                    mode='lines+markers',
                    name=stil_name,
                    hovertemplate=f"<b>{stil_name}</b><br>Datum: %{{x|%Y-%m}}<br>Begehungen: %{{y}}<extra></extra>"
                ))
        
        fig_time_styles.update_layout(
            title='Begehungen pro Monat nach Stil',
            xaxis_title='Monat',
            yaxis_title='Anzahl Begehungen',
            hovermode="x unified" # Verbessert die Hover-Erfahrung
        )
        st.plotly_chart(apply_plotly_background(fig_time_styles), use_container_width=True)
    else:
        st.info("Nicht genügend Daten oder 'stil'-Spalte fehlt für die Stil-Entwicklung.")


    st.subheader("🤝 Kletterpartner*innen")
    if 'partnerin' in ascents.columns:
        partner_counts = ascents['partnerin'].dropna().value_counts().reset_index()
        partner_counts.columns = ['Partner*in', 'Anzahl']
        
        # Erstelle eine Spalte für zufällige X- und Y-Koordinaten, um sie zu verteilen
        # Dies ist eine Heuristik, um sie "freischwebend" aussehen zu lassen
        partner_counts['rand_x'] = [i * 0.1 + (hash(p) % 100) / 1000 for i, p in enumerate(partner_counts['Partner*in'])]
        partner_counts['rand_y'] = [i * 0.1 + (hash(p) % 100) / 1000 for i, p in enumerate(partner_counts['Partner*in'])]

        fig_bubble_free = go.Figure()
        
        for index, row in partner_counts.iterrows():
            fig_bubble_free.add_trace(go.Scatter(
                x=[row['rand_x']],
                y=[row['rand_y']],
                mode='markers+text',
                marker=dict(
                    size=row['Anzahl'] * 8 + 20, # Größe basierend auf Anzahl, Mindestgröße
                    sizemode='diameter',
                    color=px.colors.qualitative.Plotly[index % len(px.colors.qualitative.Plotly)], # Farben für jeden Partner
                    line=dict(width=1, color='DarkSlateGrey')
                ),
                text=[row['Partner*in']],
                textposition='middle center',
                textfont=dict(
                    size=12 + row['Anzahl'] * 2, # Textgröße an Blasengröße anpassen
                    color='black'
                ),
                name=row['Partner*in'],
                hovertemplate=f"<b>{row['Partner*in']}</b><br>Anzahl: %{{Anzahl}}<extra></extra>"
            ))

        fig_bubble_free.update_layout(
            title='Häufigkeit der Kletterpartner*innen',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=''), # Achsen ausblenden
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=''), # Achsen ausblenden
            showlegend=False,
            hovermode="closest",
            height=500,
            margin=dict(l=20, r=20, t=50, b=20) # Ränder anpassen
        )
        st.plotly_chart(apply_plotly_background(fig_bubble_free), use_container_width=True)
    else:
        st.info("Nicht genügend Daten oder 'partnerin'-Spalte fehlt für die Partner-Statistik.")

# Hinweis: Der if __name__ == "__main__": Block wird entfernt, da diese Datei als Modul importiert wird.
