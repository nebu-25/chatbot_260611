# ✈️ Travel Chatbot

An AI-powered travel assistant built with Streamlit and OpenAI's GPT models.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chatbot-template.streamlit.app/)

## Features

### Chat
- **Language toggle** — switch between English and 한국어 from the sidebar; all UI and AI responses follow the selected language; API key is preserved across language switches
- **Model selection** — choose between GPT-4o-mini (default), GPT-4o, and GPT-3.5-turbo
- **Streaming responses** — assistant replies are streamed in real time via a background thread
- **Stop generation** — click **⬛ Stop generating** to interrupt a response mid-stream; the partial reply is saved to the conversation history
- **Voice input** — click the microphone button, speak, and the app transcribes your speech via OpenAI Whisper and sends it automatically
- **Image input** — attach a JPG, PNG, or WebP image (auto-compressed to ≤1024px); GPT-4o / GPT-4o-mini will analyze it alongside your message
- **Copy button** — every message has a 📋 popover to copy the text to clipboard
- **Regenerate** — re-send the last user message for a fresh response
- **Clear chat** — reset all messages, map pins, and attachments at once
- **Conversation history** — messages persist across reruns within a session (last 20 kept)
- **Export chat** — download the conversation as JSON, plain text, or PDF
- **Error handling** — user-friendly messages for invalid API key, rate limit, network, and API errors

### Trip Planner (sidebar)
- **Country & city selector** — choose from 39 countries and ~200 cities across Asia, Europe, the Americas, and more; select "Other" to type a destination manually
- **Destination recommendations** — personalized suggestions based on budget, duration, and travel style
- **Itinerary planner** — auto-generated day-by-day itinerary for a given destination and date range
- **Restaurants & attractions** — local picks filtered by style, atmosphere, and budget
- **Transportation guide** — flight, train, bus options and local transit tips
- Quick-action buttons auto-generate prompts from your sidebar inputs (destination, dates, budget, style)

### Currency Converter (sidebar)
- Convert between 12 currencies (USD, EUR, KRW, JPY, GBP, CNY, AUD, CAD, HKD, SGD, THB, VND)
- Rates fetched from [Frankfurter API](https://www.frankfurter.app/) — no API key required, cached for 1 hour

### Map
- Automatically extracts place names from assistant responses and geocodes them
- Pins displayed on an interactive Folium map with numbered markers
- Markers connected in order by a dashed route polyline
- Popup on each marker includes a direct **Google Maps** link
- Place list with a clear-pins button

## How to run

> **Note:** This app is designed to run on [Streamlit Cloud](https://streamlit.io/cloud). Dependencies are installed automatically from `requirements.txt` on deployment.

To run locally:

1. Install the requirements

   ```
   pip install -r requirements.txt
   ```

2. Run the app

   ```
   streamlit run streamlit_app.py
   ```

3. Enter your [OpenAI API key](https://platform.openai.com/account/api-keys) to start chatting.

## Requirements

- Python 3.9+
- OpenAI API key (Chat + Whisper — Whisper is ~$0.006/min; Vision billed per token)

---

## 이슈 관리

### ✅ 해결된 이슈

| 날짜 | 이슈 | 해결 방법 |
|---|---|---|
| 2026-06-11 | `.claude/settings.local.json` (Claude Code 설정 파일)이 실수로 커밋·푸시됨 | `git rm --cached`로 추적 해제 후 `.gitignore`에 `.claude/` 추가 |
| 2026-06-11 | `.gitignore`에 `.claude/` 항목 누락으로 내부 도구 파일 노출 위험 | `.gitignore` 업데이트 완료 |
| 2026-06-11 | 언어 전환 시 OpenAI API 키가 초기화되는 버그 | 언어 토글 시 API 키 상태 유지하도록 수정 |

### 🔶 알려진 이슈 (미해결)

| 우선순위 | 이슈 | 설명 |
|---|---|---|
| 높음 | **Streamlit Cloud 배포 URL 미설정** | README 배지가 기본 템플릿 URL(`chatbot-template.streamlit.app`)을 가리키고 있어 실제 배포 URL로 교체 필요 |
| 중간 | **환율 API 외부 의존** | Frankfurter API 장애 시 환율 변환 기능 중단 |
| 낮음 | **PDF 내보내기 한글 폰트 미지원** | PDF 출력 시 한글이 깨질 수 있음 |
