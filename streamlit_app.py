import base64
import io
import json
import queue
import threading
import time
import folium
import requests
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from fpdf import FPDF
from PIL import Image
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError

MAX_MESSAGES = 20
VISION_MODELS = {"gpt-4o", "gpt-4o-mini"}
IMAGE_MAX_PX = 1024
CURRENCIES = ["USD", "EUR", "KRW", "JPY", "GBP", "CNY", "AUD", "CAD", "HKD", "SGD", "THB", "VND"]

COUNTRY_CITIES = {
    # Asia
    "Cambodia":     ["Phnom Penh", "Siem Reap"],
    "China":        ["Beijing", "Chengdu", "Guangzhou", "Guilin", "Shanghai", "Xi'an", "Zhangjiajie"],
    "India":        ["Agra", "Goa", "Jaipur", "Mumbai", "New Delhi", "Varanasi"],
    "Indonesia":    ["Bali", "Jakarta", "Lombok", "Yogyakarta"],
    "Japan":        ["Fukuoka", "Hiroshima", "Kyoto", "Nara", "Osaka", "Sapporo", "Tokyo"],
    "Malaysia":     ["Kuala Lumpur", "Langkawi", "Penang"],
    "Nepal":        ["Kathmandu", "Pokhara"],
    "Philippines":  ["Boracay", "Cebu", "Manila", "Palawan"],
    "Singapore":    ["Singapore"],
    "South Korea":  ["Busan", "Gyeongju", "Incheon", "Jeju Island", "Jeonju", "Seoul"],
    "Taiwan":       ["Hualien", "Kaohsiung", "Tainan", "Taichung", "Taipei"],
    "Thailand":     ["Bangkok", "Chiang Mai", "Koh Samui", "Krabi", "Pattaya", "Phuket"],
    "Vietnam":      ["Da Nang", "Hanoi", "Ho Chi Minh City", "Hoi An", "Hue", "Nha Trang"],
    # Middle East & Africa
    "Egypt":        ["Alexandria", "Aswan", "Cairo", "Hurghada", "Luxor"],
    "Morocco":      ["Casablanca", "Chefchaouen", "Fez", "Marrakech", "Rabat"],
    "South Africa": ["Cape Town", "Durban", "Johannesburg"],
    "UAE":          ["Abu Dhabi", "Dubai"],
    # Europe
    "Austria":         ["Innsbruck", "Salzburg", "Vienna"],
    "Czech Republic":  ["Cesky Krumlov", "Prague"],
    "France":          ["Bordeaux", "Lyon", "Marseille", "Nice", "Paris", "Strasbourg"],
    "Germany":         ["Berlin", "Cologne", "Frankfurt", "Hamburg", "Heidelberg", "Munich"],
    "Greece":          ["Athens", "Crete", "Mykonos", "Rhodes", "Santorini"],
    "Hungary":         ["Budapest"],
    "Italy":           ["Florence", "Milan", "Naples", "Rome", "Venice"],
    "Netherlands":     ["Amsterdam", "Rotterdam", "Utrecht"],
    "Portugal":        ["Algarve", "Lisbon", "Porto", "Sintra"],
    "Spain":           ["Barcelona", "Granada", "Ibiza", "Madrid", "Seville", "Valencia"],
    "Switzerland":     ["Geneva", "Interlaken", "Lucerne", "Zermatt", "Zurich"],
    "Turkey":          ["Antalya", "Bodrum", "Cappadocia", "Istanbul", "Pamukkale"],
    "United Kingdom":  ["Bath", "Cambridge", "Edinburgh", "Liverpool", "London", "Manchester", "Oxford"],
    # Americas & Oceania
    "Argentina":    ["Buenos Aires", "Mendoza", "Patagonia"],
    "Australia":    ["Brisbane", "Cairns", "Gold Coast", "Melbourne", "Perth", "Sydney"],
    "Brazil":       ["Iguazu Falls", "Rio de Janeiro", "Salvador", "São Paulo"],
    "Canada":       ["Banff", "Montreal", "Quebec City", "Toronto", "Vancouver"],
    "Mexico":       ["Cancun", "Mexico City", "Oaxaca", "Playa del Carmen", "Tulum"],
    "New Zealand":  ["Auckland", "Christchurch", "Queenstown", "Wellington"],
    "Peru":         ["Arequipa", "Cusco", "Lima", "Machu Picchu"],
    "United States": ["Boston", "Chicago", "Hawaii", "Las Vegas", "Los Angeles", "Miami",
                      "Nashville", "New Orleans", "New York", "San Francisco", "Seattle", "Washington D.C."],
}
_COUNTRY_LIST = [""] + sorted(COUNTRY_CITIES.keys()) + ["__other__"]

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
        "country_label": "Country",
        "city_label": "City",
        "select_country": "-- Select a country --",
        "select_city": "-- Select a city --",
        "destination_other": "Other (type manually)",
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
        "currency_header": "Currency Converter",
        "currency_amount": "Amount",
        "currency_from": "From",
        "currency_to": "To",
        "currency_result": "{amount:,.0f} {fc} = {result:,.2f} {tc}",
        "currency_err": "Exchange rate unavailable.",
        "export_header": "Export Chat",
        "btn_download_json": "Download as JSON",
        "btn_download_txt": "Download as Text",
        "btn_download_pdf": "Download as PDF",
        "no_messages": "No messages to export yet.",
        "btn_clear_chat": "Clear chat",
        "map_label": "Map",
        "pinned_places": "Pinned places",
        "btn_clear_pins": "Clear pins",
        "chat_placeholder": "Ask anything about travel...",
        "img_attachment_label": "Attach image",
        "img_caption": "Attached image — will be sent with your message",
        "img_compressed": "Image resized to {w}×{h} for upload",
        "spinner_voice": "Transcribing audio...",
        "warn_voice_fail": "Speech recognition failed: {e}",
        "warn_vision_model": "Image analysis is only supported with gpt-4o / gpt-4o-mini. (Current: {model})",
        "btn_stop_gen": "⬛  Stop generating",
        "btn_regenerate": "↺  Regenerate",
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
        "country_label": "나라",
        "city_label": "도시",
        "select_country": "-- 나라 선택 --",
        "select_city": "-- 도시 선택 --",
        "destination_other": "직접 입력",
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
        "currency_header": "환율 계산기",
        "currency_amount": "금액",
        "currency_from": "통화",
        "currency_to": "환전 통화",
        "currency_result": "{amount:,.0f} {fc} = {result:,.2f} {tc}",
        "currency_err": "환율 조회 실패.",
        "export_header": "대화 내보내기",
        "btn_download_json": "JSON으로 다운로드",
        "btn_download_txt": "텍스트로 다운로드",
        "btn_download_pdf": "PDF로 다운로드",
        "no_messages": "내보낼 메시지가 없습니다.",
        "btn_clear_chat": "대화 초기화",
        "map_label": "지도",
        "pinned_places": "핀 된 장소",
        "btn_clear_pins": "핀 지우기",
        "chat_placeholder": "여행에 대해 무엇이든 물어보세요...",
        "img_attachment_label": "이미지 첨부",
        "img_caption": "첨부된 이미지 — 메시지를 보내면 함께 전송됩니다",
        "img_compressed": "이미지가 {w}×{h}로 압축되었습니다",
        "spinner_voice": "음성 인식 중...",
        "warn_voice_fail": "음성 인식 실패: {e}",
        "warn_vision_model": "이미지 분석은 gpt-4o / gpt-4o-mini 모델만 지원합니다. (현재: {model})",
        "btn_stop_gen": "⬛  생성 중지",
        "btn_regenerate": "↺  다시 생성",
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
        "You are an expert travel assistant. Help users with:\n"
        "- Personalized travel destination recommendations based on budget, duration, and style\n"
        "- Day-by-day travel itineraries\n"
        "- Local restaurant and attraction recommendations by genre, atmosphere, and budget\n"
        "- Transportation options (flights, trains, buses) and route guidance\n\n"
        "Always provide specific, actionable recommendations with place names, estimated costs where relevant, "
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


@st.cache_data(show_spinner=False)
def geocode_place(name):
    try:
        location = geolocator.geocode(name, timeout=5)
        if location:
            return {"name": name, "lat": location.latitude, "lng": location.longitude}
    except (GeocoderTimedOut, GeocoderServiceError):
        pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_exchange_rate(base, target):
    try:
        r = requests.get(
            f"https://api.frankfurter.app/latest?from={base}&to={target}", timeout=5
        )
        return r.json()["rates"][target]
    except Exception:
        return None


def compress_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    orig_size = img.size
    w, h = img.size
    if max(w, h) > IMAGE_MAX_PX:
        ratio = IMAGE_MAX_PX / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg", img.size, orig_size


def _text_of(content):
    if isinstance(content, list):
        return " ".join(p["text"] for p in content if p["type"] == "text")
    return content


def _has_image(content):
    return isinstance(content, list) and any(p["type"] == "image_url" for p in content)


def generate_pdf(messages):
    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()
    font_set = False
    for fname in ("DejaVuSans.ttf", "NotoSans-Regular.ttf"):
        try:
            pdf.add_font("Unicode", fname=fname, uni=True)
            pdf.set_font("Unicode", size=11)
            font_set = True
            break
        except Exception:
            pass
    if not font_set:
        pdf.set_font("Helvetica", size=11)

    pdf.set_font_size(16)
    pdf.cell(0, 10, "Travel Chatbot - Chat History", ln=True)
    pdf.ln(4)

    for m in messages:
        role = t("role_user") if m["role"] == "user" else t("role_assistant")
        content = _text_of(m["content"]) if isinstance(m["content"], list) else m["content"]
        img_suffix = t("img_note") if _has_image(m["content"]) else ""

        pdf.set_font_size(8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 5, f"[{role}{img_suffix}]", ln=True)
        pdf.set_text_color(30, 30, 30)
        pdf.set_font_size(10)
        pdf.multi_cell(0, 6, content)
        pdf.ln(3)

    return bytes(pdf.output())


def render_map(locations):
    lats = [p["lat"] for p in locations]
    lngs = [p["lng"] for p in locations]
    center = [sum(lats) / len(lats), sum(lngs) / len(lngs)]
    zoom = 12 if len(locations) == 1 else 4

    m = folium.Map(location=center, zoom_start=zoom)

    if len(locations) > 1:
        folium.PolyLine(
            [[p["lat"], p["lng"]] for p in locations],
            color="#4f46e5", weight=2.5, opacity=0.7, dash_array="6 4",
        ).add_to(m)

    for i, place in enumerate(locations, 1):
        gmaps_url = (
            f"https://www.google.com/maps/search/?api=1"
            f"&query={place['lat']},{place['lng']}"
        )
        popup_html = (
            f"<b>{place['name']}</b><br>"
            f"<a href='{gmaps_url}' target='_blank'>Google Maps →</a>"
        )
        folium.Marker(
            location=[place["lat"], place["lng"]],
            tooltip=f"{i}. {place['name']}",
            popup=folium.Popup(popup_html, max_width=220),
            icon=folium.Icon(color="red", icon="map-marker"),
        ).add_to(m)
    return m


def start_stream(client, model, prompt, image_b64=None, image_mime=None):
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

    # May raise auth/rate-limit errors immediately — caller handles them
    stream = client.chat.completions.create(
        model=model, messages=api_messages, stream=True
    )

    chunk_queue: queue.Queue = queue.Queue()
    stop_event = threading.Event()

    def _run():
        try:
            for chunk in stream:
                if stop_event.is_set():
                    break
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    chunk_queue.put(delta)
        except Exception as exc:
            chunk_queue.put(("__error__", exc))
        finally:
            chunk_queue.put(None)  # sentinel

    thread = threading.Thread(target=_run, daemon=True)
    st.session_state.messages.append({"role": "assistant", "content": ""})
    st.session_state["_streaming"] = True
    st.session_state["_chunk_queue"] = chunk_queue
    st.session_state["_stop_event"] = stop_event
    st.session_state["_stop_requested"] = False
    thread.start()


# ── Language selector ────────────────────────────────────────────────────────

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

openai_api_key = st.text_input(t("api_key_label"), type="password", key="openai_api_key")
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

        selected_country = st.selectbox(
            t("country_label"),
            _COUNTRY_LIST,
            format_func=lambda x: t("select_country") if x == "" else (t("destination_other") if x == "__other__" else x),
            key="trip_country",
        )

        # Reset city when country changes
        if st.session_state.get("_trip_prev_country") != selected_country:
            st.session_state["_trip_prev_country"] = selected_country
            st.session_state["trip_city"] = ""

        if not selected_country:
            destination = ""
        elif selected_country == "__other__":
            destination = st.text_input(
                t("destination_label"),
                placeholder=t("destination_placeholder"),
                key="trip_destination_manual",
            )
        else:
            city_options = [""] + COUNTRY_CITIES[selected_country]
            selected_city = st.selectbox(
                t("city_label"),
                city_options,
                format_func=lambda x: t("select_city") if x == "" else x,
                key="trip_city",
            )
            destination = f"{selected_city}, {selected_country}" if selected_city else selected_country
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

        # ── Currency Converter ────────────────────────────────────────────
        st.divider()
        st.header(t("currency_header"))
        cur_amount = st.number_input(t("currency_amount"), min_value=1, value=100, step=10)
        c1, c2 = st.columns(2)
        with c1:
            cur_from = st.selectbox(t("currency_from"), CURRENCIES, index=CURRENCIES.index("USD"), key="cur_from")
        with c2:
            cur_to = st.selectbox(t("currency_to"), CURRENCIES, index=CURRENCIES.index("KRW"), key="cur_to")
        if cur_from != cur_to:
            rate = fetch_exchange_rate(cur_from, cur_to)
            if rate:
                st.success(t("currency_result").format(
                    amount=cur_amount, fc=cur_from, result=cur_amount * rate, tc=cur_to
                ))
            else:
                st.warning(t("currency_err"))

        # ── Export Chat ───────────────────────────────────────────────────
        st.divider()
        st.header(t("export_header"))

        if "messages" in st.session_state and st.session_state.messages:
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

            try:
                pdf_bytes = generate_pdf(export_msgs)
                st.download_button(
                    label=t("btn_download_pdf"),
                    data=pdf_bytes,
                    file_name="chat_history.pdf",
                    mime="application/pdf",
                )
            except Exception:
                pass

            st.divider()
            if st.button(t("btn_clear_chat"), use_container_width=True, type="secondary"):
                st.session_state.messages = []
                st.session_state.locations = []
                st.session_state.pending_image = None
                st.session_state.pending_prompt = None
                st.rerun()
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
    if "_streaming" not in st.session_state:
        st.session_state["_streaming"] = False
    if "_stop_requested" not in st.session_state:
        st.session_state["_stop_requested"] = False

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

    stream_in_progress = st.session_state.get("_streaming", False)

    # Chat messages with copy button (skip in-progress assistant message)
    render_up_to = -1 if stream_in_progress else len(st.session_state.messages)
    for message in st.session_state.messages[:render_up_to]:
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
            with st.popover("📋", use_container_width=False):
                st.code(_text_of(content), language=None)

    # ── Streaming section ─────────────────────────────────────────────────────
    if stream_in_progress:
        cq: queue.Queue = st.session_state.get("_chunk_queue")
        stop_ev: threading.Event = st.session_state.get("_stop_event")
        stop_req = st.session_state.get("_stop_requested", False)

        # Drain all available chunks into session state
        new_text = ""
        done = False
        stream_error = None
        if cq:
            while True:
                try:
                    item = cq.get_nowait()
                    if item is None:
                        done = True
                        break
                    elif isinstance(item, tuple) and item[0] == "__error__":
                        stream_error = item[1]
                        done = True
                        break
                    new_text += item
                except queue.Empty:
                    break

        if new_text:
            st.session_state.messages[-1]["content"] += new_text

        current_text = st.session_state.messages[-1]["content"]

        with st.chat_message("assistant"):
            msg_ph = st.empty()
            if done or stop_req:
                msg_ph.markdown(current_text)
            else:
                msg_ph.markdown(current_text + "▌")
                if st.button(t("btn_stop_gen"), key="stop_gen"):
                    st.session_state["_stop_requested"] = True
                    if stop_ev:
                        stop_ev.set()

        if done or stop_req:
            final_text = st.session_state.messages[-1]["content"]
            st.session_state["_streaming"] = False
            st.session_state["_stop_requested"] = False

            if not final_text:
                st.session_state.messages.pop()  # remove empty assistant placeholder

            if stream_error and not final_text:
                st.session_state.messages.pop()  # remove user message too
                if isinstance(stream_error, AuthenticationError):
                    st.error(t("err_auth"), icon="🔑")
                elif isinstance(stream_error, RateLimitError):
                    st.error(t("err_rate"), icon="⏳")
                elif isinstance(stream_error, APIConnectionError):
                    st.error(t("err_connection"), icon="🌐")
                elif isinstance(stream_error, APIStatusError):
                    st.error(t("err_api").format(code=stream_error.status_code, message=stream_error.message), icon="⚠️")

            if final_text:
                new_places = extract_locations(client, final_text)
                for place in new_places:
                    if not any(p["name"] == place for p in st.session_state.locations):
                        geocoded = geocode_place(place)
                        if geocoded:
                            st.session_state.locations.append(geocoded)

            st.rerun()
        else:
            time.sleep(0.2)
            st.rerun()

    # Regenerate button (only when not streaming)
    if (
        not stream_in_progress
        and st.session_state.messages
        and st.session_state.messages[-1]["role"] == "assistant"
    ):
        if st.button(t("btn_regenerate"), key="regenerate"):
            st.session_state.messages.pop()
            last_user = st.session_state.messages.pop()
            raw = last_user["content"]
            if isinstance(raw, list):
                st.session_state.pending_prompt = " ".join(
                    p["text"] for p in raw if p["type"] == "text"
                )
                img_parts = [p for p in raw if p["type"] == "image_url"]
                if img_parts:
                    data_url = img_parts[0]["image_url"]["url"]
                    mime = data_url.split(";")[0].split(":")[1]
                    b64 = data_url.split(",")[1]
                    st.session_state.pending_image = {"b64": b64, "mime": mime}
            else:
                st.session_state.pending_prompt = raw
            st.rerun()

    # Resolve pending prompt
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
        compressed, mime, new_size, orig_size = compress_image(image_bytes)
        st.session_state.pending_image = {
            "b64": base64.b64encode(compressed).decode(),
            "mime": mime,
        }
        st.image(compressed, width=220, caption=t("img_caption"))
        if new_size != orig_size:
            st.caption(t("img_compressed").format(w=new_size[0], h=new_size[1]))

    # Voice input
    col_input, col_mic = st.columns([11, 1])
    with col_input:
        text_prompt = st.chat_input(t("chat_placeholder"), disabled=stream_in_progress)
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

    if prompt and not stream_in_progress:
        pending_img = st.session_state.pending_image
        if pending_img and model not in VISION_MODELS:
            st.warning(t("warn_vision_model").format(model=model), icon="⚠️")
        else:
            try:
                start_stream(
                    client, model, prompt,
                    image_b64=pending_img["b64"] if pending_img else None,
                    image_mime=pending_img["mime"] if pending_img else None,
                )
                st.session_state.pending_image = None
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
