import streamlit as st
from streamlit_geolocation import streamlit_geolocation
import requests
import pandas as pd
from datetime import datetime

# ── Must be first ────────────────────────────────────────────────────────────
st.set_page_config(page_title="BioScout Islamabad", layout="centered")

API_URL = "http://127.0.0.1:8000/api/observations/"

st.title("🦜 BioScout Islamabad")
page = st.sidebar.radio("Navigate", ["Submit Observation", "View Observations"])

# ── Submit Observation Page ───────────────────────────────────────────────────
if page == "Submit Observation":
    st.header("📸 Submit a New Observation")

    # 1. Image upload (mobile will open camera)
    img_file = st.file_uploader("Capture Image", type=["jpg", "jpeg", "png"])

    # 2. Manual species entry
    species = st.text_input("Species Name (optional)")

    # 3. Location section
    st.markdown("📍 **Location**")
    # Initialize session-state for lat/lon
    if "latitude" not in st.session_state:
        st.session_state.latitude = ""
    if "longitude" not in st.session_state:
        st.session_state.longitude = ""

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("📍 Get Location"):
            loc = streamlit_geolocation()
            # loc is a dict: {'latitude':…, 'longitude':…, 'accuracy':…, …}
            if loc and loc.get("latitude") and loc.get("longitude"):
                st.session_state.latitude = str(loc["latitude"])
                st.session_state.longitude = str(loc["longitude"])
            else:
                st.warning("⚠️ Location unavailable or permission denied.")
    with col2:
        st.text_input("Latitude", value=st.session_state.latitude, key="lat_input")
    with col3:
        st.text_input("Longitude", value=st.session_state.longitude, key="lon_input")

    # 4. Date & notes
    date = st.date_input("Date Observed", value=datetime.now().date())
    notes = st.text_area("Notes (optional)")

    # 5. Submit button
    if st.button("Submit Observation"):
        lat = st.session_state.latitude
        lon = st.session_state.longitude

        if not img_file or not lat or not lon:
            st.error("⚠️ Please provide image, latitude, and longitude.")
        else:
            try:
                files = {"image": img_file.getvalue()}
                payload = {
                    "species_name": species or "Unknown",
                    "latitude": lat,
                    "longitude": lon,
                    "date_observed": date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "notes": notes
                }
                resp = requests.post(API_URL, data=payload, files={"image": img_file})
                if resp.status_code == 201:
                    st.success("✅ Observation submitted!")
                    # Reset location fields
                    st.session_state.latitude = ""
                    st.session_state.longitude = ""
                else:
                    st.error(f"❌ Submission failed: {resp.text}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# ── View Observations Page ────────────────────────────────────────────────────
elif page == "View Observations":
    st.header("🗺️ View All Observations")

    try:
        resp = requests.get(API_URL)
        if resp.status_code == 200:
            records = resp.json()
            if records:
                df = pd.DataFrame(records)
                df['date_observed'] = pd.to_datetime(df['date_observed'])
                st.map(df.rename(columns={"latitude": "lat", "longitude": "lon"}))
                st.dataframe(df[[
                    "species_name", "date_observed", "latitude", "longitude", "notes"
                ]])
            else:
                st.info("ℹ️ No observations yet.")
        else:
            st.error(f"Failed to load data (status {resp.status_code}).")
    except Exception as e:
        st.error(f"❌ Error loading observations: {e}")
