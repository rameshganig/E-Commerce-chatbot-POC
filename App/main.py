from pathlib import Path
import streamlit as st
#from router import router
from faq import faq_chain
from sql import sql_chain

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="E-Commerce FAQ Chatbot", page_icon="💬")
st.title("E-Commerce FAQ Chatbot")

# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

def get_router():
    # Use the safe routing wrapper from router.py (returns a route name or fallback)
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

def ask(query):
    # Use the safe cached router wrapper instead of calling router directly
    route = get_bot_route(query)
    if route.name == "faq":
        return faq_chain(query)
    elif route.name == "sql":
        return sql_chain(query)   
    else:
        return "Sorry, I couldn't understand your query. Please try again."

# --- Display Conversation History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Handle Chat Input ---
query = st.chat_input("Ask a question about our products or services:")
if query:
    # 1. Render and save user question immediately
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.messages.append({"role": "user", "content": query})
    
    # 2. Get response safely
    with st.spinner("Thinking..."):
        response = ask(query)
    
    # 3. Render and save bot answer
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
