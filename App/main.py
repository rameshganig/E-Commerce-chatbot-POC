import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Now keep your existing SQLite patch right below it:
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from pathlib import Path
import streamlit as st

from faq import faq_chain
from sql import sql_chain
from smalltalk import talk   # ✅ ADD THIS


# --- Streamlit Page Configuration ---
st.set_page_config(page_title="E-Commerce FAQ Chatbot", page_icon="💬")
st.title("E-Commerce FAQ Chatbot")


# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []


# =====================================================
# ROUTER WRAPPER
# =====================================================
def get_router():
    from router import safe_route
    return safe_route


# --- Cached Routing Logic ---
def get_bot_route(user_query):
    try:
        router_fn = get_router()
        return router_fn(user_query)
    except Exception:
        st.warning("Routing fallback activated.")

        class DefaultRoute:
            name = "faq"

        return DefaultRoute()


# =====================================================
# MAIN DISPATCH FUNCTION (UPDATED WITH SMALLTALK)
# =====================================================
def ask(query):
    route = get_bot_route(query)

    if route.name == "faq":
        return faq_chain(query)

    elif route.name == "sql":
        return sql_chain(query)

    # 🔥 SMALL TALK HANDLER (GROQ LLM)
    elif route.name == "small_talk":
        return talk(query)

    else:
        return "Sorry, I couldn't understand your query. Please try again."


# --- Display Conversation History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- Handle Chat Input ---
query = st.chat_input("Ask a question about our products or services:")

if query:

    # 1. User message
    with st.chat_message("user"):
        st.markdown(query)

    st.session_state.messages.append(
        {"role": "user", "content": query}
    )

    # 2. Get response
    with st.spinner("Thinking..."):
        response = ask(query)

    # 3. Bot message
    with st.chat_message("assistant"):
        st.markdown(response)

    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )