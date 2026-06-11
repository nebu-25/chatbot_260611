# ✈️ Travel Chatbot

An AI-powered travel assistant built with Streamlit and OpenAI's GPT models.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chatbot-template.streamlit.app/)

## Features

### Chat
- **Model selection** — choose between GPT-5.4-mini (default), GPT-4o, GPT-4o-mini, and GPT-3.5-turbo
- **Streaming responses** — assistant replies are streamed in real time
- **Conversation history** — messages persist across reruns within a session
- **Error handling** — user-friendly messages for invalid API key, rate limit, network, and API errors
- **Conversation length limit** — automatically trims to the last 20 messages to prevent token limit errors
- **Export chat** — download the conversation as a JSON or plain text file

### Trip Planner (sidebar)
- **Destination recommendations** — personalized suggestions based on budget, duration, and travel style
- **Itinerary planner** — auto-generated day-by-day itinerary for a given destination and date range
- **Restaurants & attractions** — local picks filtered by style, atmosphere, and budget
- **Transportation guide** — flight, train, bus options and local transit tips
- Quick-action buttons auto-generate prompts from your sidebar inputs (destination, dates, budget, style)

### Map
- Automatically extracts place names from assistant responses
- Geocodes and pins locations on an interactive Folium map
- Place list with a clear-pins button

## How to run

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
- OpenAI API key
