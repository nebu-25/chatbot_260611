# 💬 Chatbot

A Streamlit chatbot app powered by OpenAI's GPT models.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chatbot-template.streamlit.app/)

## Features

- **Model selection** — choose between GPT-5.4-mini (default), GPT-4o, GPT-4o-mini, and GPT-3.5-turbo from the sidebar
- **Streaming responses** — assistant replies are streamed in real time
- **Conversation history** — messages persist across reruns within a session
- **Export chat** — download the conversation as a JSON or plain text file
- **Error handling** — user-friendly messages for invalid API key, rate limit, network errors, and other API failures
- **Conversation length limit** — automatically trims to the last 20 messages to prevent token limit errors

## How to run

1. Install the requirements

   ```
   pip install -r requirements.txt
   ```

2. Run the app

   ```
   streamlit run streamlit_app.py
   ```

3. Enter your [OpenAI API key](https://platform.openai.com/account/api-keys) in the text field to start chatting.
