import json
import folium
import streamlit as st
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError

MAX_MESSAGES = 20

geolocator = Nominatim(user_agent="chatbot_260611")


def extract_locations(client, text):
    """Extract place names from assistant response using OpenAI."""
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
                        "If there are no place names, return {\"places\": []}."
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
    zoom = 12 if len(locations) == 1 else 5

    m = folium.Map(location=center, zoom_start=zoom)
    for place in locations:
        folium.Marker(
            location=[place["lat"], place["lng"]],
            tooltip=place["name"],
            popup=folium.Popup(place["name"], max_width=200),
            icon=folium.Icon(color="red", icon="map-marker"),
        ).add_to(m)
    return m


st.title("💬 Chatbot")
st.write(
    "This is a simple chatbot that uses OpenAI's GPT models to generate responses. "
    "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys)."
)

openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    client = OpenAI(api_key=openai_api_key)

    # Sidebar: model selection and export
    with st.sidebar:
        st.header("Settings")
        model = st.selectbox(
            "Model",
            ["gpt-5.4-mini", "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            index=0,
        )

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
            text_data = "\n".join(lines)
            st.download_button(
                label="Download as Text",
                data=text_data,
                file_name="chat_history.txt",
                mime="text/plain",
            )
        else:
            st.caption("No messages to export yet.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "locations" not in st.session_state:
        st.session_state.locations = []

    # Map section
    if st.session_state.locations:
        with st.expander("Map", expanded=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st_folium(render_map(st.session_state.locations), width=500, height=350, returned_objects=[])
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

    if prompt := st.chat_input("What is up?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if len(st.session_state.messages) > MAX_MESSAGES:
            st.session_state.messages = st.session_state.messages[-MAX_MESSAGES:]

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            )

            with st.chat_message("assistant"):
                response = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})

            # Extract and geocode locations from response
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
