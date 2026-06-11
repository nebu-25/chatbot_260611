import json
import streamlit as st
from openai import OpenAI

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
            ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            index=0,
        )

        st.divider()
        st.header("Export Chat")

        if "messages" in st.session_state and st.session_state.messages:
            # JSON download
            json_data = json.dumps(st.session_state.messages, ensure_ascii=False, indent=2)
            st.download_button(
                label="Download as JSON",
                data=json_data,
                file_name="chat_history.json",
                mime="application/json",
            )

            # Plain text download
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

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is up?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

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
