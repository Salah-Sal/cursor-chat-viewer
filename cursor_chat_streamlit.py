import streamlit as st
import os
# import sqlite3 # No longer needed directly here
# import json # No longer needed directly here
import platform
from pathlib import Path
from collections import defaultdict
import traceback
import chat_utils # Add this line near the top

# --- Core Data Loading Functions ---

# REMOVE the old load_all_chat_data function (lines 17-67)

# Add the new wrapper function with caching
@st.cache_data
def load_data_wrapper():
     try:
         # sessions_data, total_messages, total_sessions = load_all_chat_data() # Old call
         sessions_data, file_histories = chat_utils.load_all_workspace_data() # New call
         total_messages = sum(len(chats) for chats in sessions_data.values())
         total_sessions = len(sessions_data)
         return sessions_data, file_histories, total_messages, total_sessions
     except FileNotFoundError as e:
          st.error(str(e))
          return None, None, 0, 0
     except Exception as e:
          st.error(f"An unexpected error occurred during data loading: {e}")
          st.code(traceback.format_exc()) # Show details if something else goes wrong
          return None, None, 0, 0

# --- Streamlit App UI ---

st.set_page_config(page_title="Cursor Chat Viewer", layout="wide")
st.title("🔎 Cursor Chat History Viewer")

# Load data using the wrapper
with st.spinner("Loading history from database files..."):
    # sessions_data, total_messages, total_sessions = load_all_chat_data() # Old call
    sessions_data, file_histories, total_messages, total_sessions = load_data_wrapper() # New call

if sessions_data is None: # Error occurred during loading
     st.stop()

st.write(f"Parsed **{total_messages}** messages across **{total_sessions}** unique chat sessions.")
st.write(f"Found file history for **{len(file_histories)}** workspaces.") # Add this line

if not sessions_data and not file_histories: # Check if anything was loaded
    st.info("No chat sessions or file history found in the scanned databases.")
    st.stop()

# Prepare session list for display (Check if sessions_data could be empty but file_histories exist)
session_list_for_display = []
session_map = {}
if sessions_data:
    # Sort sessions for consistent display (e.g., by source then title)
    sorted_session_keys = sorted(sessions_data.keys(), key=lambda k: (k[0], sessions_data[k][0].get('chatTitle', 'Untitled Chat')))

    for i, key in enumerate(sorted_session_keys):
        chats = sessions_data[key]
        if chats:
            title = chats[0].get('chatTitle', 'Untitled Chat')
            num_messages = len(chats)
            source = key[0]
            display_name = f"{i+1}. {title} ({num_messages} messages) [{source}]"
            session_list_for_display.append(display_name)
            session_map[display_name] = key # Map display name back to key
else:
    st.info("No chat sessions found, but file history might be available.")

# Add placeholder option
options = ["-- Select a Chat Session --"] + session_list_for_display

# Only show select box if there are sessions
if session_list_for_display:
    selected_display_name = st.selectbox(
        "Choose a chat session to view:",
        options=options,
        index=0 # Default to placeholder
    )
else:
    selected_display_name = "-- Select a Chat Session --" # Ensure variable exists
    st.write("No chat sessions available to select.")

st.divider()

# Display selected chat and history
if selected_display_name != "-- Select a Chat Session --":
    selected_key = session_map[selected_display_name] # key is (workspace_id, tabId)
    selected_session_chats = sessions_data[selected_key]
    workspace_id = selected_key[0] # Get workspace ID from the key

    if selected_session_chats:
         # Display chat header and messages - existing code
         st.header(f"Chat: {selected_session_chats[0].get('chatTitle', 'Untitled Chat')}")
         st.caption(f"Source: {workspace_id} | Tab ID: {selected_key[1]}")
         for chat in selected_session_chats:
            role = chat.get('role', 'unknown')
            # Ensure role is one of the types st.chat_message expects, default to "assistant"
            if role not in ["user", "assistant"]:
                role = "assistant"
            with st.chat_message(role):
                st.markdown(chat.get('content', '[No Content]')) # Use markdown to render content (handles code blocks)

         # --- Add File History Expander ---
         st.divider()
         with st.expander(f"View File History for Workspace '{workspace_id}'"):
             history = file_histories.get(workspace_id)
             if history:
                 st.write(f"Found {len(history)} recent file entries:")
                 # Display as a simple list, maybe reversed to show newest first?
                 # Use dict.fromkeys to remove duplicates while preserving order (Python 3.7+)
                 unique_history = list(dict.fromkeys(history))
                 st.write(f"({len(unique_history)} unique files)")
                 for filepath in reversed(unique_history):
                     st.code(filepath, language=None) # Display file paths
             else:
                 st.info(f"No file history found or parsed for workspace '{workspace_id}'.")
         # --- End File History Expander ---

    else:
        # This case should ideally not happen if the session is in the selectbox
        st.write("This session appears to have no messages.")
elif not session_list_for_display and file_histories:
    # If no chats, but history exists, maybe offer to view history directly?
    st.info("Select a workspace below to view its file history:")
    workspace_options = ["-- Select Workspace --"] + sorted(list(file_histories.keys()))
    selected_workspace = st.selectbox("Workspace File History:", options=workspace_options)
    if selected_workspace != "-- Select Workspace --":
         history = file_histories.get(selected_workspace)
         if history:
            st.write(f"Found {len(history)} recent file entries for '{selected_workspace}':")
            unique_history = list(dict.fromkeys(history))
            st.write(f"({len(unique_history)} unique files)")
            for filepath in reversed(unique_history):
                 st.code(filepath, language=None)
         # No else needed, .get handles missing key
elif not session_list_for_display and not file_histories:
    # This case is handled earlier by st.stop()
    pass
else: # Placeholder selected or no sessions
    st.info("Select a chat session from the dropdown above to view its messages and associated file history.") 