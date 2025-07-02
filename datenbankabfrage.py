import streamlit as st
from supabase import create_client, Client
import pandas as pd
import os
from dotenv import load_dotenv

st.title("Simple Supabase Data Viewer")
st.write("Checking connection and data retrieval from your Supabase tables.")

# Load environment variables from the .env file
load_dotenv()

# Get Supabase URL and API key from environment variables
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Check if Supabase variables are set
if not url or not key:
    st.error("Supabase URL or API key not found in environment variables. Please check your .env file.")
    st.stop() # Stops app execution if variables are missing

# Create connection to Supabase
supabase: Client = create_client(url, key)

# Function to fetch and display regions
def display_regions():
    st.subheader("Regions (Gebiete)")
    try:
        regions_response = supabase.table("region").select("region_id, region_name").execute()
        regions_df = pd.DataFrame(regions_response.data)

        if regions_df.empty:
            st.warning("No data found in the 'region' table.")
        else:
            st.write("Data from 'region' table:")
            st.dataframe(regions_df)
            st.success(f"Successfully loaded {len(regions_df)} regions.")
            return regions_df # Return for potential use later
    except Exception as e:
        st.error(f"Error fetching data from 'region' table: {e}")
    return pd.DataFrame() # Return empty DataFrame on error

# Function to fetch and display peaks, joined with regions
def display_peaks_with_regions(regions_df):
    st.subheader("Peaks (Gipfel) with Regions")
    try:
        peaks_response = supabase.table("peaks").select("peak_id, gipfel, region_id, hoehe").execute()
        peaks_df = pd.DataFrame(peaks_response.data)

        if peaks_df.empty:
            st.warning("No data found in the 'peaks' table.")
            return

        # Ensure region_id is int for merging
        if 'region_id' in peaks_df.columns:
            peaks_df['region_id'] = peaks_df['region_id'].astype(int)
        else:
            st.error("Error: 'region_id' column not found in 'peaks' table data. Cannot join with regions.")
            return

        if not regions_df.empty:
            merged_df = peaks_df.merge(regions_df, on="region_id", how="left")
            st.write("Data from 'peaks' table, joined with 'region_name':")
            st.dataframe(merged_df[['peak_id', 'gipfel', 'region_name', 'hoehe']])
            st.success(f"Successfully loaded {len(merged_df)} peaks and joined with regions.")
        else:
            st.write("Could not join peaks with regions as no region data was loaded.")
            st.dataframe(peaks_df[['peak_id', 'gipfel', 'region_id', 'hoehe']]) # Show raw peaks data
    except Exception as e:
        st.error(f"Error fetching data from 'peaks' table: {e}")

# Main app function
def app():
    # Display regions first
    regions_df = display_regions()

    # Then display peaks, using the regions_df if it was successfully loaded
    display_peaks_with_regions(regions_df)

if __name__ == "__main__":
    app()
