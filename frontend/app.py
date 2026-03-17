"""
BioScout — AI-Powered Wildlife Observation Platform
Streamlit frontend with 6 pages: Home, Submit, View, AI Identifier, Q&A Chat, About.
"""

import sys
from pathlib import Path

# Allow importing from frontend/utils.py
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="🌿 BioScout",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
from datetime import datetime, date
import folium
from streamlit_folium import st_folium

import utils

# ── Session State Defaults ────────────────────────────────────────────────────
for key, default in {
    "token": None,
    "username": None,
    "chat_history": [],
    "page": "🏠 Home",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌿 BioScout")
    st.markdown("*AI-Powered Wildlife Observer*")
    st.divider()

    page = st.radio(
        "Navigate",
        [
            "🏠 Home",
            "📸 Submit Observation",
            "🗺️ View Observations",
            "🤖 AI Species Identifier",
            "💬 Species Q&A Chat",
            "ℹ️ About",
        ],
        label_visibility="collapsed",
    )
    st.session_state.page = page

    st.divider()

    # Auth section
    if st.session_state.token:
        st.markdown(
            f"<div style='color:#AABBC8;font-size:0.85rem;padding:4px 0;'>👤 {st.session_state.username}</div>",
            unsafe_allow_html=True,
        )
        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.username = None
            st.rerun()
    else:
        with st.expander("🔐 Login / Register"):
            auth_tab = st.radio("", ["Login", "Register"], horizontal=True)
            if auth_tab == "Login":
                uname = st.text_input("Username", key="login_user")
                pwd = st.text_input("Password", type="password", key="login_pwd")
                if st.button("Login", use_container_width=True):
                    result = utils.login(uname, pwd)
                    if result:
                        st.session_state.token = result["access"]
                        st.session_state.username = result["user"]["username"]
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
            else:
                new_user = st.text_input("Username", key="reg_user")
                new_email = st.text_input("Email", key="reg_email")
                new_pwd = st.text_input("Password", type="password", key="reg_pwd")
                if st.button("Register", use_container_width=True):
                    ok, msg = utils.register(new_user, new_email, new_pwd)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    st.divider()

    # Knowledge base stats
    st.markdown("**📊 Knowledge Base**")
    try:
        from observations.rag.vector_store import SpeciesVectorStore
        vs = SpeciesVectorStore()
        kb_stats = vs.get_stats()
        n = kb_stats.get("total_documents", 0)
        if n > 0:
            st.caption(f"✅ {n} species indexed")
            st.caption("Hybrid BM25 + Vector search")
        else:
            st.caption("⏳ Building knowledge base...")
    except Exception:
        st.caption("⏳ Building knowledge base...")


# ── Helper: confidence badge ──────────────────────────────────────────────────
def confidence_badge(score: float) -> str:
    """Return a coloured HTML badge for a confidence score."""
    pct = int(score * 100)
    if score >= 0.8:
        color = "#2ECC71"
    elif score >= 0.5:
        color = "#F39C12"
    else:
        color = "#E74C3C"
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:12px;font-size:0.75rem;font-weight:600;">{pct}%</span>'
    )


CATEGORY_COLORS = {
    "bird": "blue",
    "mammal": "red",
    "reptile": "green",
    "insect": "orange",
    "plant": "darkgreen",
    "other": "gray",
}


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Home":
    st.markdown(
        """
        <div style='text-align:center;padding:2rem 0 1rem;'>
            <h1 style='font-size:2.8rem;'>🌿 BioScout</h1>
            <h3 style='color:#2ECC71;font-weight:400;'>AI-Powered Wildlife Observer</h3>
            <p style='color:#AABBC8;font-size:1.1rem;max-width:600px;margin:auto;'>
                Discover, identify and track wildlife using the power of artificial intelligence.
                Built for Pakistan and South Asia.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Metric cards
    with st.spinner("Loading stats..."):
        stats = utils.get_stats()

    if stats:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔭 Total Observations", stats["total_observations"])
        c2.metric("🦎 Unique Species", stats["unique_species"])
        c3.metric("📅 This Week", stats["observations_this_week"])
        c4.metric("🤖 AI Identified", stats["ai_identifications_total"])
    else:
        st.warning("Could not load stats. Is the Django server running?")

    st.divider()

    # Recent observations
    st.subheader("🕐 Recent Observations")
    with st.spinner("Loading recent observations..."):
        data = utils.get_observations(page=1)

    if data and data.get("results"):
        recent = data["results"][:5]
        cols = st.columns(min(len(recent), 5))
        for i, obs in enumerate(recent):
            with cols[i]:
                conf = obs.get("prediction_confidence", 0)
                cat = obs.get("category", "other")
                dt = obs.get("date_observed", "")[:10]
                st.markdown(
                    f"""
                    <div style='background:#1A2634;border-radius:10px;padding:1rem;
                                border-left:4px solid #2ECC71;'>
                        <div style='font-size:1.1rem;font-weight:700;'>{obs['species_name']}</div>
                        <div style='color:#2ECC71;font-size:0.8rem;text-transform:uppercase;
                                    letter-spacing:1px;'>{cat}</div>
                        <div style='color:#AABBC8;font-size:0.8rem;margin-top:4px;'>📅 {dt}</div>
                        <div style='margin-top:6px;'>{confidence_badge(conf)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No observations yet. Submit the first one!")

    st.divider()

    # Category breakdown
    if stats and stats.get("observations_by_category"):
        st.subheader("📊 Observations by Category")
        cat_data = {
            k: v
            for k, v in stats["observations_by_category"].items()
            if v > 0
        }
        if cat_data:
            df_cat = pd.DataFrame(
                list(cat_data.items()), columns=["Category", "Count"]
            )
            st.bar_chart(df_cat.set_index("Category"), color="#2ECC71")

    st.divider()

    # How It Works section
    st.subheader("🚀 How It Works")
    hw1, hw2, hw3 = st.columns(3)
    for col, icon, title, desc in [
        (hw1, "📸", "Upload Photo", "Take a photo of any wildlife — bird, mammal, reptile, plant, or insect."),
        (hw2, "🤖", "AI Analysis", "DeepSeek Vision identifies the species with confidence score and ecological details."),
        (hw3, "📊", "Track & Learn", "Save to your observation log, explore the map, and ask the RAG chatbot anything."),
    ]:
        with col:
            st.markdown(
                f"""
                <div style='background:#1A2634;border-radius:12px;padding:1.5rem;
                            text-align:center;height:160px;'>
                    <div style='font-size:2.5rem;'>{icon}</div>
                    <div style='font-weight:700;font-size:1rem;margin:8px 0 4px;'>{title}</div>
                    <div style='color:#AABBC8;font-size:0.85rem;'>{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SUBMIT OBSERVATION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📸 Submit Observation":
    st.title("📸 Submit a New Observation")

    if not st.session_state.token:
        st.warning("🔐 Please login from the sidebar to submit observations.")
        st.stop()

    col_form, col_map = st.columns([1, 1])

    with col_form:
        species = st.text_input("Species Name", placeholder="e.g. House Sparrow")
        category = st.selectbox(
            "Category",
            ["bird", "mammal", "reptile", "insect", "plant", "other"],
        )
        description = st.text_area(
            "Description / Notes",
            placeholder="Describe what you observed...",
            height=100,
        )
        lat = st.number_input(
            "Latitude", value=33.7215, format="%.6f", step=0.0001
        )
        lon = st.number_input(
            "Longitude", value=73.0433, format="%.6f", step=0.0001
        )
        obs_date = st.date_input("Date Observed", value=date.today())
        img_file = st.file_uploader(
            "Upload Image", type=["jpg", "jpeg", "png"]
        )

        if img_file:
            st.image(img_file, caption="Preview", use_container_width=True)

    with col_map:
        st.markdown("**📍 Selected Location**")
        m = folium.Map(location=[lat, lon], zoom_start=12)
        folium.Marker(
            [lat, lon],
            popup=species or "Observation",
            icon=folium.Icon(color="green", icon="leaf"),
        ).add_to(m)
        st_folium(m, height=380, use_container_width=True)

    st.divider()

    if st.button("✅ Submit Observation", use_container_width=True, type="primary"):
        if not species:
            st.error("Please enter a species name.")
        elif not img_file:
            st.error("Please upload an image.")
        else:
            payload = {
                "species_name": species,
                "category": category,
                "latitude": lat,
                "longitude": lon,
                "date_observed": obs_date.strftime("%Y-%m-%dT00:00:00Z"),
                "notes": description,
            }
            with st.spinner("Submitting..."):
                ok, msg = utils.submit_observation(
                    payload, img_file.getvalue(), st.session_state.token
                )
            if ok:
                st.success(f"✅ {msg}")
                st.balloons()
            else:
                st.error(f"❌ {msg}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: VIEW OBSERVATIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗺️ View Observations":
    st.title("🗺️ View Observations")

    # Filters
    with st.expander("🔍 Filters", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            f_species = st.text_input("Search species", placeholder="e.g. eagle")
        with fc2:
            f_category = st.selectbox(
                "Category", ["", "bird", "mammal", "reptile", "insect", "plant", "other"]
            )
        with fc3:
            f_date_from = st.date_input("From date", value=None)
        with fc4:
            f_date_to = st.date_input("To date", value=None)

    view_mode = st.radio("View", ["🗂️ Grid View", "🗺️ Map View"], horizontal=True)

    # Pagination
    if "obs_page" not in st.session_state:
        st.session_state.obs_page = 1

    with st.spinner("Loading observations..."):
        data = utils.get_observations(
            page=st.session_state.obs_page,
            species=f_species,
            category=f_category,
            date_from=str(f_date_from) if f_date_from else "",
            date_to=str(f_date_to) if f_date_to else "",
        )

    if not data:
        st.error("❌ Could not load observations. Is the Django server running?")
        st.stop()

    observations = data.get("results", [])
    total_count = data.get("count", 0)
    total_pages = max(1, (total_count + 9) // 10)

    st.caption(f"Showing {len(observations)} of {total_count} observations — Page {st.session_state.obs_page}/{total_pages}")

    if view_mode == "🗂️ Grid View":
        if not observations:
            st.info("No observations match your filters.")
        else:
            # Category placeholder config
            CAT_PLACEHOLDER = {
                "bird":    ("🦜", "linear-gradient(135deg,#1a472a,#2ECC71)"),
                "mammal":  ("🦁", "linear-gradient(135deg,#3d2b1f,#8B5E3C)"),
                "reptile": ("🐍", "linear-gradient(135deg,#1a2e1a,#4a7c4a)"),
                "plant":   ("🌿", "linear-gradient(135deg,#1a3a1a,#6abf69)"),
                "insect":  ("🦋", "linear-gradient(135deg,#2a1a3a,#9b59b6)"),
                "other":   ("🔍", "linear-gradient(135deg,#2a2a2a,#555)"),
            }
            # 3-column grid
            for row_start in range(0, len(observations), 3):
                cols = st.columns(3)
                for col_idx, obs in enumerate(observations[row_start:row_start + 3]):
                    with cols[col_idx]:
                        conf = obs.get("prediction_confidence", 0)
                        cat = obs.get("category", "other")
                        dt = obs.get("date_observed", "")[:10]
                        img_url = obs.get("image", "")
                        if img_url:
                            st.image(img_url, use_container_width=True)
                        else:
                            emoji, gradient = CAT_PLACEHOLDER.get(cat, CAT_PLACEHOLDER["other"])
                            st.markdown(
                                f"""<div style='background:{gradient};border-radius:8px;
                                    height:160px;display:flex;align-items:center;
                                    justify-content:center;font-size:4rem;
                                    margin-bottom:4px;'>{emoji}</div>""",
                                unsafe_allow_html=True,
                            )
                        st.markdown(
                            f"""
                            <div style='background:#1A2634;border-radius:8px;
                                        padding:0.75rem;margin-bottom:0.5rem;'>
                                <div style='font-weight:700;font-size:1rem;'>
                                    {obs['species_name']}
                                </div>
                                <div style='color:#2ECC71;font-size:0.75rem;
                                            text-transform:uppercase;'>{cat}</div>
                                <div style='color:#AABBC8;font-size:0.75rem;'>
                                    📍 {obs['latitude']:.3f}, {obs['longitude']:.3f}
                                </div>
                                <div style='color:#AABBC8;font-size:0.75rem;'>📅 {dt}</div>
                                <div style='margin-top:6px;'>{confidence_badge(conf)}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

    else:  # Map View
        if observations:
            center_lat = sum(o["latitude"] for o in observations) / len(observations)
            center_lon = sum(o["longitude"] for o in observations) / len(observations)
        else:
            center_lat, center_lon = 30.3753, 69.3451  # Pakistan center

        m = folium.Map(location=[center_lat, center_lon], zoom_start=6)

        for obs in observations:
            cat = obs.get("category", "other")
            color = CATEGORY_COLORS.get(cat, "gray")
            conf = obs.get("prediction_confidence", 0)
            popup_html = f"""
                <b>{obs['species_name']}</b><br>
                Category: {cat}<br>
                Date: {obs.get('date_observed','')[:10]}<br>
                Confidence: {int(conf*100)}%<br>
                {obs.get('notes','')[:80]}
            """
            folium.CircleMarker(
                location=[obs["latitude"], obs["longitude"]],
                radius=8,
                color=color,
                fill=True,
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=obs["species_name"],
            ).add_to(m)

        st_folium(m, height=500, use_container_width=True)

    # Pagination controls
    st.divider()
    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        if st.button("← Previous") and st.session_state.obs_page > 1:
            st.session_state.obs_page -= 1
            st.rerun()
    with p2:
        st.markdown(
            f"<div style='text-align:center;'>Page {st.session_state.obs_page} / {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with p3:
        if st.button("Next →") and st.session_state.obs_page < total_pages:
            st.session_state.obs_page += 1
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: AI SPECIES IDENTIFIER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 AI Species Identifier":
    st.title("🤖 AI Species Identifier")
    st.markdown(
        "Upload a photo of any wildlife and our AI will identify the species "
        "using DeepSeek Vision + iNaturalist."
    )

    if not st.session_state.token:
        st.warning("🔐 Please login from the sidebar to use AI identification.")
        st.stop()

    col_upload, col_result = st.columns([1, 1])

    with col_upload:
        st.markdown("### 📤 Upload Image")
        img_file = st.file_uploader(
            "Drag and drop or click to upload",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
        )
        if img_file:
            st.image(img_file, caption="Uploaded image", use_container_width=True)

        lat = st.number_input("Latitude", value=33.7215, format="%.6f")
        lon = st.number_input("Longitude", value=73.0433, format="%.6f")

        identify_btn = st.button(
            "🔍 Identify Species", use_container_width=True, type="primary"
        )

    with col_result:
        st.markdown("### 🧬 Identification Result")

        if identify_btn:
            if not img_file:
                st.error("Please upload an image first.")
            else:
                with st.spinner("🔬 Analyzing image with AI..."):
                    result = utils.identify_species(
                        img_file.getvalue(), lat, lon, st.session_state.token
                    )

                if result:
                    species = result.get("species", "Unknown")
                    confidence = result.get("confidence", 0)
                    method = result.get("method", "Unknown")
                    details = result.get("species_details", "")

                    st.markdown(f"## {species}")
                    st.caption(f"Identified via: **{method}**")

                    st.markdown("**Confidence Score**")
                    st.progress(float(confidence))
                    st.markdown(confidence_badge(confidence), unsafe_allow_html=True)

                    if details:
                        st.divider()
                        st.markdown("**📖 Species Details**")
                        st.markdown(details)

                    # Conservation status colour
                    st.divider()
                    inat_url = f"https://www.inaturalist.org/taxa/search?q={species.replace(' ', '+')}"
                    st.link_button("🔗 View on iNaturalist", inat_url)

                    obs_id = result.get("observation_id")
                    if obs_id:
                        st.success(f"✅ Saved as Observation #{obs_id}")
                else:
                    st.error("❌ Identification failed. Check your API key and server.")
        else:
            st.markdown("**Example results**")
            for ex_name, ex_conf, ex_emoji in [
                ("Snow Leopard", 0.94, "🦁"),
                ("House Sparrow", 0.89, "🦜"),
                ("Spectacled Cobra", 0.82, "🐍"),
            ]:
                pct = int(ex_conf * 100)
                bar_w = pct
                st.markdown(
                    f"""
                    <div style='background:#1A2634;border-radius:10px;padding:12px 16px;
                                margin-bottom:8px;opacity:0.75;'>
                        <div style='font-size:1.1rem;font-weight:700;'>
                            {ex_emoji} {ex_name}
                        </div>
                        <div style='background:#0F1923;border-radius:6px;
                                    height:8px;margin:8px 0;overflow:hidden;'>
                            <div style='background:#2ECC71;width:{bar_w}%;height:100%;
                                        border-radius:6px;'></div>
                        </div>
                        <div style='color:#AABBC8;font-size:0.8rem;'>
                            Confidence: {pct}%
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.caption("Upload an image to get real AI identification")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SPECIES Q&A CHAT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💬 Species Q&A Chat":
    st.title("💬 Species Q&A Chat")
    st.caption("🧠 Powered by DeepSeek + RAG Knowledge Base (52 species | Hybrid BM25 + Vector | 100% accuracy)")

    if not st.session_state.token:
        st.warning("🔐 Please login from the sidebar to use the chatbot.")
        st.stop()

    use_rag = st.sidebar.toggle("🧠 Use RAG Knowledge Base", value=True)

    # Clear chat
    if st.sidebar.button("🗑️ Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

    # Suggested questions — shown only when chat is empty
    if not st.session_state.chat_history:
        st.markdown("**💡 Try asking:**")
        suggestions = [
            "🐆 What do snow leopards eat?",
            "🦜 Common birds in Lahore?",
            "🐍 Venomous reptiles in Pakistan?",
            "🌳 Sacred trees in South Asia?",
        ]
        s_cols = st.columns(4)
        for i, suggestion in enumerate(suggestions):
            with s_cols[i]:
                if st.button(suggestion, use_container_width=True, key=f"sug_{i}"):
                    st.session_state._pending_question = suggestion.split(" ", 1)[1]
                    st.rerun()
        st.divider()

    # Handle pending question from suggestion chips
    pending = st.session_state.pop("_pending_question", None)

    # Chat history display
    for msg in st.session_state.chat_history:
        role = msg["role"]
        content = msg["content"]
        sources = msg.get("sources", [])
        scores = msg.get("scores", [])
        ts = msg.get("timestamp", "")

        if role == "user":
            st.markdown(
                f"""
                <div style='display:flex;justify-content:flex-end;margin:8px 0;'>
                    <div style='max-width:70%;'>
                        <div style='background:#2ECC71;color:#0F1923;padding:10px 16px;
                                    border-radius:18px 18px 4px 18px;font-weight:500;'>
                            {content}
                        </div>
                        <div style='text-align:right;color:#6B7F8E;font-size:0.7rem;
                                    margin-top:2px;'>{ts}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style='display:flex;justify-content:flex-start;margin:8px 0;'>
                    <div style='max-width:75%;'>
                        <div style='background:#1A2634;color:#ECEFF1;padding:10px 16px;
                                    border-radius:18px 18px 18px 4px;'>
                            {content}
                        </div>
                        {f'<div style="color:#6B7F8E;font-size:0.75rem;margin-top:4px;">📚 Sources: {", ".join(sources)}</div>' if sources else ''}
                        <div style='color:#6B7F8E;font-size:0.7rem;margin-top:2px;'>{ts}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # Input form
    with st.form("chat_form", clear_on_submit=True):
        fc1, fc2 = st.columns([5, 1])
        with fc1:
            user_input = st.text_input(
                "Ask a question...",
                value=pending or "",
                placeholder="e.g. What do snow leopards eat?",
                label_visibility="collapsed",
            )
        with fc2:
            send = st.form_submit_button("Send", use_container_width=True)

    # Auto-send if came from suggestion chip
    auto_send = pending is not None

    if (send and user_input.strip()) or (auto_send and pending):
        question = (user_input or pending).strip()
        now_str = datetime.now().strftime("%H:%M")
        st.session_state.chat_history.append(
            {"role": "user", "content": question, "timestamp": now_str}
        )

        with st.spinner("🤖 BioScout AI is thinking..."):
            if use_rag:
                result = utils.ask_rag_question(question, st.session_state.token)
                if result:
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": result.get("answer", "No answer."),
                            "sources": result.get("sources", []),
                            "scores": result.get("retrieval_scores", []),
                            "timestamp": datetime.now().strftime("%H:%M"),
                        }
                    )
                else:
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": "❌ RAG service unavailable. Try again.",
                            "sources": [],
                            "scores": [],
                            "timestamp": datetime.now().strftime("%H:%M"),
                        }
                    )
            else:
                result = utils.ask_species_question(
                    question, "wildlife in Pakistan", st.session_state.token
                )
                if result:
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": result.get("answer", "No answer."),
                            "sources": [],
                            "scores": [],
                            "timestamp": datetime.now().strftime("%H:%M"),
                        }
                    )
                else:
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": "❌ AI service unavailable.",
                            "sources": [],
                            "scores": [],
                            "timestamp": datetime.now().strftime("%H:%M"),
                        }
                    )
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ABOUT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "ℹ️ About":
    st.title("ℹ️ About BioScout")

    st.markdown(
        """
        **BioScout** is an AI-powered wildlife observation platform built for Pakistan
        and South Asia. It allows citizen scientists, researchers, and nature enthusiasts
        to document, identify, and track wildlife using cutting-edge AI.

        The platform combines **DeepSeek Vision** for image-based species identification
        with a **RAG (Retrieval-Augmented Generation)** knowledge base containing 50+
        species documents, enabling grounded, factual Q&A without hallucinations.
        """
    )

    st.divider()
    st.subheader("🛠️ Tech Stack")

    tech = {
        "🐍 Backend": "Django 5 + Django REST Framework",
        "🎨 Frontend": "Streamlit",
        "🤖 AI / LLM": "DeepSeek V3 (Vision + Chat)",
        "🧠 RAG": "ChromaDB + BM25 Hybrid Retrieval",
        "🗄️ Database": "SQLite (dev) / PostgreSQL (prod)",
        "🔐 Auth": "JWT via djangorestframework-simplejwt",
        "📖 API Docs": "drf-spectacular (Swagger UI)",
        "🗺️ Maps": "Folium + streamlit-folium",
        "🚀 Deployment": "Railway (backend) + Streamlit Cloud (frontend)",
    }

    for tech_name, tech_desc in tech.items():
        st.markdown(f"- **{tech_name}**: {tech_desc}")

    st.divider()
    st.subheader("🧠 RAG Architecture")
    st.markdown(
        """
        ```
        User Question
              ↓
        Hybrid Retriever
         ├── BM25 keyword search (rank_bm25)
         └── Vector semantic search (ChromaDB + all-MiniLM-L6-v2)
              ↓
        Reciprocal Rank Fusion (score merging)
              ↓
        Top-3 Species Documents (context)
              ↓
        DeepSeek LLM (grounded answer)
              ↓
        Answer + Sources + Confidence
        ```

        The hybrid approach combines **BM25** (great for exact keyword matches like
        species names) with **vector search** (great for semantic similarity like
        "animals that hunt at night"). Reciprocal Rank Fusion merges both ranked
        lists into a single score, giving better results than either alone.
        """
    )

    st.divider()
    st.subheader("👤 Author")
    st.markdown(
        """
        Built by **Malik Ibrar** — AI Engineer

        [![GitHub](https://img.shields.io/badge/GitHub-MalikkIbrar-181717?logo=github)](https://github.com/MalikkIbrar/BioScout)
        """
    )
    st.link_button("⭐ Star on GitHub", "https://github.com/MalikkIbrar/BioScout")
