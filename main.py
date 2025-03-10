import streamlit as st
import requests
import json
from uuid import uuid4

st.set_page_config(page_title="Chat with Bot", page_icon="💬")

st.markdown("# Chat with Bot 💬")
st.sidebar.markdown("# Settings")

with st.sidebar:
    bot_url = st.text_input(
        "Bot URL",
        value="http://localhost:8080",
        key="bot_url"
    )
    classifier_url = st.text_input(
        "Classifier URL",
        value="http://84.201.150.171:443",
        key="classifier_url"
    )

    if st.button("Reset Chat"):
        st.session_state.pop("messages", None)
        st.session_state.pop("classifications", None)
        st.session_state.pop("dialog_id", None)
        st.session_state.pop("last_message_id", None)

if "messages" not in st.session_state:
    st.session_state["messages"] = [{
        "role": "assistant",
        "content": "Hello! I'm a bot. How can I help you today?"
    }]

if "classifications" not in st.session_state:
    st.session_state["classifications"] = [{
        "role": "assistant",
        "content": "Hello! I'm a bot. How can I help you today?",
        "probability": None
    }]

if "dialog_id" not in st.session_state:
    st.session_state["dialog_id"] = str(uuid4())

if "last_message_id" not in st.session_state:
    st.session_state["last_message_id"] = None

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if i < len(st.session_state.classifications) and st.session_state.classifications[i].get(
                "probability") is not None:
            st.caption(f"Bot probability: {st.session_state.classifications[i]['probability']:.4f}")


def send_to_bot(message, url, dialog_id, last_message_id):
    try:
        payload = {
            "dialog_id": dialog_id,
            "last_msg_text": message,
            "last_message_id": last_message_id
        }

        response = requests.post(f"{url}/get_message", json=payload)

        if response.status_code == 200:
            response_data = response.json()
            return response_data.get("new_msg_text", "No response received"), response_data.get("dialog_id")
        else:
            return f"Error: Received status code {response.status_code}", dialog_id
    except Exception as e:
        return f"Error communicating with bot: {str(e)}", dialog_id


def classify_message(message, dialog_id, message_id, participant_index, url):
    try:
        payload = {
            "text": message,
            "dialog_id": dialog_id,
            "id": message_id,
            "participant_index": participant_index
        }

        response = requests.post(f"{url}/predict", json=payload)

        if response.status_code == 200:
            response_data = response.json()
            return response_data.get("is_bot_probability")
        else:
            st.sidebar.error(f"Classifier error: {response.status_code}")
            return None
    except Exception as e:
        st.sidebar.error(f"Error communicating with classifier: {str(e)}")
        return None


if message := st.chat_input("Type a message..."):
    current_message_id = str(uuid4())

    user_msg = {"role": "user", "content": message}
    st.session_state.messages.append(user_msg)
    st.chat_message("user").write(message)

    user_prob = classify_message(
        message,
        st.session_state.dialog_id,
        current_message_id,
        0,
        st.session_state.classifier_url
    )

    user_classification = {
        "role": "user",
        "content": message,
        "probability": user_prob
    }
    st.session_state.classifications.append(user_classification)

    if user_prob is not None:
        st.chat_message("user").caption(f"Bot probability: {user_prob:.4f}")

    bot_response, dialog_id = send_to_bot(
        message,
        st.session_state.bot_url,
        st.session_state.dialog_id,
        current_message_id
    )

    st.session_state.dialog_id = dialog_id
    st.session_state.last_message_id = current_message_id

    bot_message_id = str(uuid4())

    bot_msg = {"role": "assistant", "content": bot_response}
    st.session_state.messages.append(bot_msg)
    with st.chat_message("assistant"):
        st.write(bot_response)

        bot_prob = classify_message(
            bot_response,
            st.session_state.dialog_id,
            bot_message_id,
            1,
            st.session_state.classifier_url
        )

        bot_classification = {
            "role": "assistant",
            "content": bot_response,
            "probability": bot_prob
        }
        st.session_state.classifications.append(bot_classification)

        if bot_prob is not None:
            st.caption(f"Bot probability: {bot_prob:.4f}")
