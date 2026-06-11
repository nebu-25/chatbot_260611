import base64
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
VISION_MODELS = {"gpt-4o", "gpt-4o-mini"}

TRANSLATIONS = {
    "en": {
        "title": "✈️ Travel Chatbot",
        "intro": (
            "Your AI travel assistant — get destination recommendations, itineraries, "
            "restaurant picks, and transportation tips. "
            "Provide your [OpenAI API key](https://platform.openai.com/account/api-keys) to start."
        ),
        "api_key_label": "OpenAI API Key",
        "api_key_info": "Please add your OpenAI API key to continue.",
        "settings_header": "Settings",
        "model_label": "Model",
        "trip_planner_header": "Trip Planner",
        "destination_label": "Destination",
        "destination_placeholder": "e.g. Tokyo, Paris",
        "start_date_label": "Start date",
        "end_date_label": "End date",
        "budget_label": "Budget",
        "budget_options": ["Budget", "Moderate", "Luxury"],
        "travel_style_label": "Travel style",
        "travel_style_options": ["Adventure", "Relaxation", "Culture", "Food", "Nature", "Shopping"],
        "quick_actions_label": "**Quick actions**",
        "btn_recommend": "Recommend destinations",
        "btn_itinerary": "Create itinerary",
        "btn_restaurants": "Find restaurants & attractions",
        "btn_transport": "Transportation options",
        "warn_no_destination": "Please enter a destination first.",
        "export_header": "Export Chat",
        "btn_download_json": "Download as JSON",
        "btn_download_txt": "Download as Text",
        "no_messages": "No messages to export yet.",
        "map_label": "Map",
        "pinned_places": "Pinned places",
        "btn_clear_pins": "Clear pins",
        "chat_placeholder": "Ask anything about travel...",
        "img_attachment_label": "Attach image",
        "img_caption": "Attached image — will be sent with your message",
        "spinner_voice": "Transcribing audio...",
        "warn_voice_fail": "Speech recognition failed: {e}",
        "warn_vision_model": "Image analysis is only supported with gpt-4o / gpt-4o-mini. (Current: {model})",
        "role_user": "User",
        "role_assistant": "Assistant",
        "img_note": " [Image attached]",
        "err_auth": "Invalid API key. Please check your OpenAI API key and try again.",
        "err_rate": "Rate limit exceeded. Please wait a moment and try again.",
        "err_connection": "Network error. Please check your internet connection and try again.",
        "err_api": "API error ({code}): {message}",
        "prompt_recommend": (
            "Recommend travel destinations for a {budget} budget traveler who enjoys {styles}. {duration}"
        ),
        "prompt_itinerary": (
            "Create a detailed day-by-day itinerary for {destination} {date_str}. "
            "Budget level: {budget}. Travel style: {styles}."
        ),
        "prompt_restaurants": (
            "Recommend the best restaurants and must-see attractions in {destination}. "
            "Budget level: {budget}. Preferred style: {styles}."
        ),
        "prompt_transport": (
            "What are the best transportation options to reach {destination} "
            "and get around locally? Include flights, trains, buses, and local transit tips."
        ),
        "prompt_date_range": "from {start} to {end} ({days} days)",
        "prompt_default_days": "for 3 days",
        "prompt_default_style": "general",
        "prompt_local_style": "local",
        "system_lang": "Respond in English.",
    },
    "ko": {
        "title": "✈️ 여행 챗봇",
        "intro": (
            "AI 여행 도우미 — 여행지 추천, 일정 계획, 맛집 및 관광지 정보, 교통 정보를 알려드립니다. "
            "시작하려면 [OpenAI API 키](https://platform.openai.com/account/api-keys)를 입력하세요."
        ),
        "api_key_label": "OpenAI API 키",
        "api_key_info": "계속하려면 OpenAI API 키를 입력해 주세요.",
        "settings_header": "설정",
        "model_label": "모델",
        "trip_planner_header": "여행 플래너",
        "destination_label": "여행지",
        "destination_placeholder": "예: 도쿄, 파리",
        "start_date_label": "출발일",
        "end_date_label": "귀국일",
        "budget_label": "예산",
        "budget_options": ["저렴", "보통", "럭셔리"],
        "travel_style_label": "여행 스타일",
        "travel_style_options": ["모험", "휴양", "문화", "맛집", "자연", "쇼핑"],
        "quick_actions_label": "**빠른 실행**",
        "btn_recommend": "여행지 추천",
        "btn_itinerary": "일정 만들기",
        "btn_restaurants": "맛집 & 관광지 찾기",
        "btn_transport": "교통 수단 안내",
        "warn_no_destination": "먼저 여행지를 입력해 주세요.",
        "export_header": "대화 내보내기",
        "btn_download_json": "JSON으로 다운로드",
        "btn_download_txt": "텍스트로 다운로드",
        "no_messages": "내보낼 메시지가 없습니다.",
        "map_label": "지도",
        "pinned_places": "핀 된 장소",
        "btn_clear_pins": "핀 지우기",
        "chat_placeholder": "여행에 대해 무엇이든 물어보세요...",
        "img_attachment_label": "이미지 첨부",
        "img_caption": "첨부된 이미지 — 메시지를 보내면 함께 전송됩니다",
        "spinner_voice": "음성 인식 중...",
        "warn_voice_fail": "음성 인식 실패: {e}",
        "warn_vision_model": "이미지 분석은 gpt-4o / gpt-4o-mini 모델만 지원합니다. (현재: {model})",
        "role_user": "사용자",
        "role_assistant": "도우미",
        "img_note": " [이미지 첨부]",
        "err_auth": "API 키가 올바르지 않습니다. OpenAI API 키를 확인하고 다시 시도해 주세요.",
        "err_rate": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.",
        "err_connection": "네트워크 오류가 발생했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.",
        "err_api": "API 오류 ({code}): {message}",
        "prompt_recommend": (
            "{budget} 예산으로 {styles}을(를) 즐기는 여행자에게 적합한 여행지를 추천해 주세요. {duration}"
        ),
        "prompt_itinerary": (
            "{destination} {date_str} 상세 일정을 만들어 주세요. "
            "예산 수준: {budget}. 여행 스타일: {styles}."
        ),
        "prompt_restaurants": (
            "{destination}의 최고 맛집과 꼭 가봐야 할 관광지를 추천해 주세요. "
            "예산 수준: {budget}. 선호 스타일: {styles}."
        ),
        "prompt_transport": (
            "{destination}까지 가는 방법과 현지 이동 수단을 알려주세요. "
            "항공편, 기차, 버스, 대중교통 정보를 포함해 주세요."
        ),
        "prompt_date_range": "{start}부터 {end}까지 ({days}일)",
        "prompt_default_days": "3일 일정으로",
        "prompt_default_style": "일반",
        "prompt_local_style": "현지",
        "system_lang": "한국어로 답변해 주세요.",
    },
}


def t(key):
    lang = st.session_state.get("lang", "en")
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))


def get_system_prompt():
    return (
        f"You are an expert travel assistant. Help users with:\n"
        f"- Personalized travel destination recommendations based on budget, duration, and style\n"
        f"- Day-by-day travel itineraries\n"
        f"- Local restaurant and attraction recommendations by genre, atmosphere, and budget\n"
        f"- Transportation options (flights, trains, buses) and route guidance\n\n"
        f"Always provide specific, actionable recommendations with place names, estimated costs where relevant, "
        f"and practical tips. {t('system_lang')}"
    )


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


def send_message(client, model, prompt, image_b64=None, image_mime=None):
    """Append user message, call API, return response. Raises on API error."""
    if image_b64:
        content = [
            {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{image_b64}"}},
            {"type": "text", "text": prompt},
        ]
    else:
        content = prompt

    st.session_state.messages.append({"role": "user", "content": content})
    with st.chat_message("user"):
        if image_b64:
            st.image(f"data:{image_mime};base64,{image_b64}", width=300)
        st.markdown(prompt)

    if len(st.session_state.messages) > MAX_MESSAGES:
        st.session_state.messages = st.session_state.messages[-MAX_MESSAGES:]

    api_messages = [{"role": "system", "content": get_system_prompt()}] + [
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


# ── Language selector (always visible, before API key check) ─────────────────

if "lang" not in st.session_state:
    st.session_state.lang = "en"

with st.sidebar:
    lang_map = {"English": "en", "한국어": "ko"}
    selected_label = st.radio(
        "🌐",
        list(lang_map.keys()),
        index=list(lang_map.values()).index(st.session_state.lang),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.lang = lang_map[selected_label]

# ── App layout ───────────────────────────────────────────────────────────────

st.title(t("title"))
st.write(t("intro"))

openai_api_key = st.text_input(t("api_key_label"), type="password")
if not openai_api_key:
    st.info(t("api_key_info"), icon="🗝️")
else:
    client = OpenAI(api_key=openai_api_key)

    with st.sidebar:
        st.header(t("settings_header"))
        model = st.selectbox(
            t("model_label"),
            ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            index=0,
        )

        # ── Trip Planner ──────────────────────────────────────────────────
        st.divider()
        st.header(t("trip_planner_header"))

        destination = st.text_input(t("destination_label"), placeholder=t("destination_placeholder"))
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(t("start_date_label"), value=None)
        with col2:
            end_date = st.date_input(t("end_date_label"), value=None)

        budget_options = t("budget_options")
        budget = st.select_slider(
            t("budget_label"),
            options=budget_options,
            value=budget_options[1],
            key=f"budget_{st.session_state.lang}",
        )
        style_options = t("travel_style_options")
        styles = st.multiselect(
            t("travel_style_label"),
            style_options,
            key=f"styles_{st.session_state.lang}",
        )

        st.markdown(t("quick_actions_label"))

        if st.button(t("btn_recommend"), use_container_width=True):
            style_str = ", ".join(styles) if styles else t("prompt_default_style")
            duration = (
                f"{(end_date - start_date).days} days."
                if start_date and end_date else ""
            )
            st.session_state.pending_prompt = t("prompt_recommend").format(
                budget=budget, styles=style_str, duration=duration
            )

        if st.button(t("btn_itinerary"), use_container_width=True):
            if destination:
                date_str = (
                    t("prompt_date_range").format(
                        start=start_date, end=end_date, days=(end_date - start_date).days
                    )
                    if start_date and end_date
                    else t("prompt_default_days")
                )
                st.session_state.pending_prompt = t("prompt_itinerary").format(
                    destination=destination,
                    date_str=date_str,
                    budget=budget,
                    styles=", ".join(styles) if styles else t("prompt_default_style"),
                )
            else:
                st.warning(t("warn_no_destination"))

        if st.button(t("btn_restaurants"), use_container_width=True):
            if destination:
                st.session_state.pending_prompt = t("prompt_restaurants").format(
                    destination=destination,
                    budget=budget,
                    styles=", ".join(styles) if styles else t("prompt_local_style"),
                )
            else:
                st.warning(t("warn_no_destination"))

        if st.button(t("btn_transport"), use_container_width=True):
            if destination:
                st.session_state.pending_prompt = t("prompt_transport").format(
                    destination=destination
                )
            else:
                st.warning(t("warn_no_destination"))

        # ── Export Chat ───────────────────────────────────────────────────
        st.divider()
        st.header(t("export_header"))

        if "messages" in st.session_state and st.session_state.messages:
            def _text_of(content):
                if isinstance(content, list):
                    return " ".join(p["text"] for p in content if p["type"] == "text")
                return content

            def _has_image(content):
                return isinstance(content, list) and any(p["type"] == "image_url" for p in content)

            export_msgs = [
                {
                    "role": m["role"],
                    "content": _text_of(m["content"]),
                    **({"has_image": True} if _has_image(m["content"]) else {}),
                }
                for m in st.session_state.messages
            ]
            st.download_button(
                label=t("btn_download_json"),
                data=json.dumps(export_msgs, ensure_ascii=False, indent=2),
                file_name="chat_history.json",
                mime="application/json",
            )

            lines = []
            for m in export_msgs:
                role = t("role_user") if m["role"] == "user" else t("role_assistant")
                img_note = t("img_note") if m.get("has_image") else ""
                lines.append(f"[{role}{img_note}]\n{m['content']}\n")
            st.download_button(
                label=t("btn_download_txt"),
                data="\n".join(lines),
                file_name="chat_history.txt",
                mime="text/plain",
            )
        else:
            st.caption(t("no_messages"))

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "locations" not in st.session_state:
        st.session_state.locations = []
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None
    if "pending_image" not in st.session_state:
        st.session_state.pending_image = None

    # Map section
    if st.session_state.locations:
        with st.expander(t("map_label"), expanded=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st_folium(
                    render_map(st.session_state.locations),
                    width=500,
                    height=350,
                    returned_objects=[],
                )
            with col2:
                st.caption(t("pinned_places"))
                for place in st.session_state.locations:
                    st.markdown(f"- {place['name']}")
                if st.button(t("btn_clear_pins")):
                    st.session_state.locations = []
                    st.rerun()

    # Chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            content = message["content"]
            if isinstance(content, list):
                for part in content:
                    if part["type"] == "image_url":
                        st.image(part["image_url"]["url"], width=300)
                    elif part["type"] == "text":
                        st.markdown(part["text"])
            else:
                st.markdown(content)

    # Resolve pending prompt from quick-action buttons
    active_prompt = st.session_state.pending_prompt
    if active_prompt:
        st.session_state.pending_prompt = None

    # Image uploader
    col_upload, _ = st.columns([11, 1])
    with col_upload:
        uploaded_file = st.file_uploader(
            t("img_attachment_label"), type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed"
        )
    if uploaded_file:
        image_bytes = uploaded_file.read()
        st.session_state.pending_image = {
            "b64": base64.b64encode(image_bytes).decode(),
            "mime": uploaded_file.type,
        }
        st.image(image_bytes, width=220, caption=t("img_caption"))

    # Voice input
    col_input, col_mic = st.columns([11, 1])
    with col_input:
        text_prompt = st.chat_input(t("chat_placeholder"))
    with col_mic:
        audio_bytes = audio_recorder(text="", icon_size="lg", pause_threshold=2.0, key="mic")

    if audio_bytes and audio_bytes != st.session_state.get("_last_audio"):
        st.session_state["_last_audio"] = audio_bytes
        with st.spinner(t("spinner_voice")):
            buf = io.BytesIO(audio_bytes)
            buf.name = "audio.wav"
            try:
                transcript = client.audio.transcriptions.create(model="whisper-1", file=buf)
                st.session_state.pending_prompt = transcript.text
            except Exception as e:
                st.warning(t("warn_voice_fail").format(e=e))
        st.rerun()

    prompt = active_prompt or text_prompt

    if prompt:
        pending_img = st.session_state.pending_image
        if pending_img and model not in VISION_MODELS:
            st.warning(t("warn_vision_model").format(model=model), icon="⚠️")
        else:
            try:
                response = send_message(
                    client, model, prompt,
                    image_b64=pending_img["b64"] if pending_img else None,
                    image_mime=pending_img["mime"] if pending_img else None,
                )
                st.session_state.pending_image = None

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
                st.error(t("err_auth"), icon="🔑")
                st.session_state.messages.pop()
            except RateLimitError:
                st.error(t("err_rate"), icon="⏳")
                st.session_state.messages.pop()
            except APIConnectionError:
                st.error(t("err_connection"), icon="🌐")
                st.session_state.messages.pop()
            except APIStatusError as e:
                st.error(t("err_api").format(code=e.status_code, message=e.message), icon="⚠️")
                st.session_state.messages.pop()
