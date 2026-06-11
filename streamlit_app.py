import io
import json
import folium
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError

MAX_MESSAGES = 20

SYSTEM_PROMPT = """You are an expert travel assistant. Help users with:
- Personalized travel destination recommendations based on budget, duration, and style
- Day-by-day travel itineraries
- Local restaurant and attraction recommendations by genre, atmosphere, and budget
- Transportation options (flights, trains, buses) and route guidance

Always provide specific, actionable recommendations with place names, estimated costs where relevant,
and practical tips. Respond in the same language the user writes in."""

geolocator = Nominatim(user_agent="chatbot_260611")


def extract_locations(client, text):
    try:
        result = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract all specific place names (restaurants, landmarks, cities, "
                        "attractions, addresses) from the text. "
                        'Return JSON in the format: {"places": ["place1", "place2"]}. '
                        'If there are no place names, return {"places": []}.'
                    ),
                },
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(result.choices[0].message.content)
        return data.get("places", [])
    except Exception:
        return []


def geocode_place(name):
    try:
        location = geolocator.geocode(name, timeout=5)
        if location:
            return {"name": name, "lat": location.latitude, "lng": location.longitude}
    except (GeocoderTimedOut, GeocoderServiceError):
        pass
    return None


def render_map(locations):
    lats = [p["lat"] for p in locations]
    lngs = [p["lng"] for p in locations]
    center = [sum(lats) / len(lats), sum(lngs) / len(lngs)]
    zoom = 12 if len(locations) == 1 else 4

    m = folium.Map(location=center, zoom_start=zoom)
    for place in locations:
        folium.Marker(
            location=[place["lat"], place["lng"]],
            tooltip=place["name"],
            popup=folium.Popup(place["name"], max_width=200),
            icon=folium.Icon(color="red", icon="map-marker"),
        ).add_to(m)
    return m


def send_message(client, model, prompt):
    """Append user message, call API, return response. Raises on API error."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if len(st.session_state.messages) > MAX_MESSAGES:
        st.session_state.messages = st.session_state.messages[-MAX_MESSAGES:]

    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]

    stream = client.chat.completions.create(
        model=model, messages=api_messages, stream=True
    )
    with st.chat_message("assistant"):
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})
    return response


# ── App layout ──────────────────────────────────────────────────────────────

st.title("✈️ Travel Chatbot")
st.write(
    "Your AI travel assistant — get destination recommendations, itineraries, "
    "restaurant picks, and transportation tips. "
    "Provide your [OpenAI API key](https://platform.openai.com/account/api-keys) to start."
)

openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    client = OpenAI(api_key=openai_api_key)

    with st.sidebar:
        st.header("Settings")
        model = st.selectbox(
            "Model",
            ["gpt-5.4-mini", "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            index=0,
        )

        # ── Trip Planner ──────────────────────────────────────────────────
        st.divider()
        st.header("Trip Planner")

        destination = st.text_input("Destination", placeholder="e.g. Tokyo, Paris")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date", value=None)
        with col2:
            end_date = st.date_input("End date", value=None)

        budget = st.select_slider(
            "Budget",
            options=["Budget", "Moderate", "Luxury"],
            value="Moderate",
        )
        styles = st.multiselect(
            "Travel style",
            ["Adventure", "Relaxation", "Culture", "Food", "Nature", "Shopping"],
        )

        st.markdown("**Quick actions**")

        if st.button("Recommend destinations", use_container_width=True):
            style_str = ", ".join(styles) if styles else "general"
            st.session_state.pending_prompt = (
                f"Recommend travel destinations for a {budget.lower()} budget traveler "
                f"who enjoys {style_str}. "
                + (f"Trip duration: {(end_date - start_date).days} days." if start_date and end_date else "")
            )

        if st.button("Create itinerary", use_container_width=True):
            if destination:
                date_str = (
                    f"from {start_date} to {end_date} ({(end_date - start_date).days} days)"
                    if start_date and end_date
                    else "for 3 days"
                )
                st.session_state.pending_prompt = (
                    f"Create a detailed day-by-day itinerary for {destination} {date_str}. "
                    f"Budget level: {budget}. Travel style: {', '.join(styles) if styles else 'general'}."
                )
            else:
                st.warning("Please enter a destination first.")

        if st.button("Find restaurants & attractions", use_container_width=True):
            if destination:
                style_str = ", ".join(styles) if styles else "local"
                st.session_state.pending_prompt = (
                    f"Recommend the best restaurants and must-see attractions in {destination}. "
                    f"Budget level: {budget}. Preferred style: {style_str}."
                )
            else:
                st.warning("Please enter a destination first.")

        if st.button("Transportation options", use_container_width=True):
            if destination:
                st.session_state.pending_prompt = (
                    f"What are the best transportation options to reach {destination} "
                    f"and get around locally? Include flights, trains, buses, and local transit tips."
                )
            else:
                st.warning("Please enter a destination first.")

        # ── Export Chat ───────────────────────────────────────────────────
        st.divider()
        st.header("Export Chat")

        if "messages" in st.session_state and st.session_state.messages:
            json_data = json.dumps(st.session_state.messages, ensure_ascii=False, indent=2)
            st.download_button(
                label="Download as JSON",
                data=json_data,
                file_name="chat_history.json",
                mime="application/json",
            )

            lines = []
            for m in st.session_state.messages:
                role = "User" if m["role"] == "user" else "Assistant"
                lines.append(f"[{role}]\n{m['content']}\n")
            st.download_button(
                label="Download as Text",
                data="\n".join(lines),
                file_name="chat_history.txt",
                mime="text/plain",
            )
        else:
            st.caption("No messages to export yet.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "locations" not in st.session_state:
        st.session_state.locations = []
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None

    # Map section
    if st.session_state.locations:
        with st.expander("Map", expanded=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st_folium(
                    render_map(st.session_state.locations),
                    width=500,
                    height=350,
                    returned_objects=[],
                )
            with col2:
                st.caption("Pinned places")
                for place in st.session_state.locations:
                    st.markdown(f"- {place['name']}")
                if st.button("Clear pins"):
                    st.session_state.locations = []
                    st.rerun()

    # Chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Resolve pending prompt from quick-action buttons
    active_prompt = st.session_state.pending_prompt
    if active_prompt:
        st.session_state.pending_prompt = None

    # Voice input
    col_input, col_mic = st.columns([11, 1])
    with col_input:
        text_prompt = st.chat_input("Ask anything about travel...")
    with col_mic:
        audio_bytes = audio_recorder(text="", icon_size="lg", pause_threshold=2.0, key="mic")

    if audio_bytes and audio_bytes != st.session_state.get("_last_audio"):
        st.session_state["_last_audio"] = audio_bytes
        with st.spinner("음성 인식 중..."):
            buf = io.BytesIO(audio_bytes)
            buf.name = "audio.wav"
            try:
                transcript = client.audio.transcriptions.create(model="whisper-1", file=buf)
                st.session_state.pending_prompt = transcript.text
            except Exception as e:
                st.warning(f"음성 인식 실패: {e}")
        st.rerun()

    prompt = active_prompt or text_prompt

    if prompt:
        try:
            response = send_message(client, model, prompt)

            new_places = extract_locations(client, response)
            added = False
            for place in new_places:
                if not any(p["name"] == place for p in st.session_state.locations):
                    geocoded = geocode_place(place)
                    if geocoded:
                        st.session_state.locations.append(geocoded)
                        added = True
            if added:
                st.rerun()

        except AuthenticationError:
            st.error("Invalid API key. Please check your OpenAI API key and try again.", icon="🔑")
            st.session_state.messages.pop()
        except RateLimitError:
            st.error("Rate limit exceeded. Please wait a moment and try again.", icon="⏳")
            st.session_state.messages.pop()
        except APIConnectionError:
            st.error("Network error. Please check your internet connection and try again.", icon="🌐")
            st.session_state.messages.pop()
        except APIStatusError as e:
            st.error(f"API error ({e.status_code}): {e.message}", icon="⚠️")
            st.session_state.messages.pop()
