import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
st.set_page_config(page_title="Statistik", layout="wide")

st.markdown("""
<style>
/* === Google Fonts importieren === */
@import url('https://fonts.googleapis.com/css2?family=Georama&family=Onest:wght@600&display=swap');

/* === Gesamtseiten-Hintergrund in ocker === */
.stApp {
    background-color: #f0e68c !important;
}

/* === Headlines in Onest === */
h1, h2, h3, .stTitle, .stMarkdown h1, .stMarkdown h2 {
    font-family: 'Onest', sans-serif !important;
    color: #1e1e1e;
}

/* === Fließtext in Georama === */
html, body, .stMarkdown p, .stText, .stDataFrame, .css-18ni7ap {
    font-family: 'Georama', sans-serif !important;
    color: #222;
}

/* === Buttons in schwarz mit weißem Text === */
.stButton > button {
    background-color: #000 !important;
    color: white !important;
    border-radius: 8px;
    padding: 0.5em 1em;
    border: none;
}

.stButton > button:hover {
    background-color: #333 !important;
    transition: background-color 0.3s ease-in-out;
}

/* === Grüne Füllfarben z. B. für Plotly Balken/Donuts (empfohlen via Plotly) === */
/* Das kann bei Plotly Charts nicht direkt über CSS überschrieben werden.
   Stelle dort beim Erstellen einfach `marker_color='green'` oder ähnlich ein. */
</style>
""", unsafe_allow_html=True)



st.title("📊 Gipfel Statistik")





# .env laden
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(url, key)

@st.cache_data
def fetch_data():
    rocks = pd.DataFrame(supabase.table("rocks").select("id, sector_id").range(0, 5000).execute().data)
    ascents = pd.DataFrame(supabase.table("ascents").select("route_id, gipfel_id, stil, datum, partnerin").execute().data)
    sectors = pd.DataFrame(supabase.table("sector").select("id, name").execute().data)
    return rocks, ascents, sectors

def apply_plotly_background(fig):
    fig.update_layout(
        paper_bgcolor="#f0e68c",
        plot_bgcolor="#f0e68c"
    )
    return fig

    

def app():
    rocks, ascents, sectors = fetch_data()

    total_rocks = len(rocks)
    unique_done_rocks = ascents['gipfel_id'].dropna().astype(int).unique()
    num_done_rocks = len(unique_done_rocks)
    unique_done_routes = ascents['route_id'].dropna().astype(int).unique()
    num_done_routes = len(unique_done_routes)

    # ✅ Prozent vorher berechnen!
    percent_done = round((num_done_rocks / total_rocks) * 100, 1) if total_rocks > 0 else 0

    st.subheader("🔍 Überblick")

    ascents['datum'] = pd.to_datetime(ascents['datum'], errors='coerce')
    current_year = pd.Timestamp.now().year
    ascents_current_year = ascents[ascents['datum'].dt.year == current_year]

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
                text=[f"{row['Gipfel']}  "],  # ← 2 Leerzeichen rechts
                textposition='inside',
                insidetextfont=dict(
                    family='Onest, sans-serif',  # << deine Schriftart
                    size=24,                     # << größer für Wirkung
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


    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("\U0001F9D7 Begangene Routen", f"{num_done_routes}")

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

    st.subheader("\U0001F4CC Übersicht pro Gebiet")

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

    st.subheader("📅 Entwicklung der Begehungen")
    if 'datum' in ascents.columns:
        ascents_by_month = ascents.dropna(subset=['datum']).groupby(pd.Grouper(key='datum', freq='M')).size()
        fig_time = px.line(x=ascents_by_month.index, y=ascents_by_month.values,
                           labels={'x': 'Monat', 'y': 'Begehungen'},
                           title='Begehungen pro Monat')
        st.plotly_chart(apply_plotly_background(fig_time), use_container_width=True)

    st.subheader("\U0001F91D Kletterpartner*innen")
    if 'partnerin' in ascents.columns:
        partner_counts = ascents['partnerin'].dropna().value_counts().reset_index()
        partner_counts.columns = ['Partner*in', 'Anzahl']
        fig_bubble = px.scatter(partner_counts, x='Partner*in', y='Anzahl', size='Anzahl',
                                color='Partner*in', size_max=60,
                                title='Häufigkeit der Kletterpartner*innen')
        fig_bubble.update_layout(showlegend=False, xaxis={'visible': False}, yaxis_title='Anzahl Begehungen')
        st.plotly_chart(apply_plotly_background(fig_bubble), use_container_width=True)



if __name__ == "__main__":
    app()
