import streamlit as st
import requests

# Backend API URL
API_URL = "https://chatbot-tzjm.onrender.com"

# Set page config
st.set_page_config(
    page_title="AI Chat App",
    page_icon="💬",
    layout="wide"
)

# Initialize session state for selected thread
if "selected_thread_id" not in st.session_state:
    st.session_state.selected_thread_id = None


def create_thread(title=None):
    """Create a new thread via API."""
    payload = {"title": title} if title else {}
    response = requests.post(f"{API_URL}/threads", json=payload)
    if response.status_code == 201:
        return response.json()
    return None


def get_threads():
    """Fetch all threads via API."""
    response = requests.get(f"{API_URL}/threads")
    if response.status_code == 200:
        return response.json()
    return []


def get_thread_messages(thread_id):
    """Fetch messages for a specific thread via API."""
    response = requests.get(f"{API_URL}/threads/{thread_id}/messages")
    if response.status_code == 200:
        return response.json()
    return []


def send_message(thread_id, content):
    """Send a message to a thread and get AI response via API."""
    payload = {"content": content}
    response = requests.post(f"{API_URL}/threads/{thread_id}/messages", json=payload)
    if response.status_code == 200:
        return response.json()
    return None


# Sidebar
with st.sidebar:
    st.title("💬 AI Chat App")
    
    # New Chat button
    if st.button("+ New Chat", use_container_width=True):
        new_thread = create_thread()
        if new_thread:
            st.session_state.selected_thread_id = new_thread["id"]
            st.rerun()
    
    st.divider()
    
    # List all threads
    threads = get_threads()
    
    if threads:
        st.subheader("Conversations")
        for thread in threads:
            # Display thread title (truncate if too long)
            display_title = thread["title"][:30] + "..." if len(thread["title"]) > 30 else thread["title"]
            
            # Highlight selected thread
            if st.session_state.selected_thread_id == thread["id"]:
                button_type = "primary"
            else:
                button_type = "secondary"
            
            if st.button(display_title, key=f"thread_{thread['id']}", use_container_width=True):
                st.session_state.selected_thread_id = thread["id"]
                st.rerun()
    else:
        st.info("No conversations yet. Click '+ New Chat' to start!")


# Main area
st.title("Chat")

if st.session_state.selected_thread_id is not None:
    # Display messages for selected thread
    messages = get_thread_messages(st.session_state.selected_thread_id)
    
    # Display each message
    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if user_input := st.chat_input("Type your message..."):
        # Display user message immediately
        with st.chat_message("user"):
            st.write(user_input)
        
        # Send message to API and get response
        with st.spinner("Thinking..."):
            response = send_message(st.session_state.selected_thread_id, user_input)
            
            if response:
                # Display assistant response
                with st.chat_message("assistant"):
                    st.write(response["reply"])
            else:
                st.error("Failed to get a response. Please try again.")
else:
    # No thread selected
    if threads:
        st.info("👈 Select a conversation from the sidebar or start a new chat.")
    else:
        st.info("👈 Click '+ New Chat' in the sidebar to start your first conversation!")
