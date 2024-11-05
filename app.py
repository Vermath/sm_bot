# streamlit_app.py

import streamlit as st
import openai
from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
from pathlib import Path

# Set your OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI()

# Assistant ID
ASSISTANT_ID = "asst_APr8LHsr6M0sGabYH4Mgo5a6"

# Initialize session state
if 'thread_id' not in st.session_state:
    # Create a new thread
    thread = client.beta.threads.create()
    st.session_state['thread_id'] = thread.id
    st.session_state['messages'] = []
else:
    thread_id = st.session_state['thread_id']
    thread = client.beta.threads.retrieve(thread_id=thread_id)

# Streamlit app UI
st.title("Assistant Chat with File Search")

# Display conversation history
for message in st.session_state['messages']:
    if message['role'] == 'user':
        st.markdown(f"**You:** {message['content']}")
    else:
        st.markdown(f"**Assistant:** {message['content']}")

# Message input
with st.form(key='chat_form'):
    user_input = st.text_area("Your message:", key="user_input")
    uploaded_files = st.file_uploader(
        "Upload files for the assistant to search (optional):",
        accept_multiple_files=True,
        type=['pdf', 'txt', 'docx', 'md', 'html', 'json']
    )
    submit_button = st.form_submit_button(label='Send')

if submit_button and user_input.strip() != '':
    # Handle file uploads
    attachments = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Save the uploaded file to a temporary location
            file_path = Path(f"temp_{uploaded_file.name}")
            with open(file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            # Upload the file to OpenAI
            file_response = client.files.create(
                file=file_path,
                purpose="assistants",
            )
            # Remove the temporary file
            file_path.unlink()
            attachments.append({
                "file_id": file_response.id,
                "tools": [{"type": "file_search"}],
            })

    # Add the user's message to the thread
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input,
        attachments=attachments,
    )

    # Add message to session state messages
    st.session_state['messages'].append({
        "role": "user",
        "content": user_input,
    })

    # Define an EventHandler class
    class StreamlitEventHandler(AssistantEventHandler):
        def __init__(self, message_placeholder):
            super().__init__()  # Added this line to fix the error
            self.message_placeholder = message_placeholder
            self.message = ""

        @override
        def on_text_delta(self, delta, snapshot):
            self.message += delta.value
            self.message_placeholder.markdown(f"**Assistant:** {self.message}")

        @override
        def on_tool_call_created(self, tool_call):
            self.message += f"\n\n*Assistant is using {tool_call.type} tool...*\n"
            self.message_placeholder.markdown(f"**Assistant:** {self.message}")

        @override
        def on_message_done(self, message):
            # Add assistant's message to session state messages
            st.session_state['messages'].append({
                "role": "assistant",
                "content": self.message,
            })

    # Create a placeholder for assistant's response
    assistant_placeholder = st.empty()
    handler = StreamlitEventHandler(assistant_placeholder)

    # Create a run and stream the response
    with st.spinner("Assistant is typing..."):
        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
            event_handler=handler,
        ) as stream:
            stream.until_done()

    # Clear the input field
    st.session_state['user_input'] = ''

