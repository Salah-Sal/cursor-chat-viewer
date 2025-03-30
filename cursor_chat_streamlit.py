import streamlit as st
import os
import sqlite3
import json
import platform
from pathlib import Path
from collections import defaultdict
import traceback

# --- Core Data Loading Functions (Adapted from previous script) ---

def get_cursor_storage_path():
    """Determines the path to Cursor's workspaceStorage based on the OS."""
    system = platform.system()
    # ... (Keep the exact implementation from cursor_chat_viewer.py) ...
    if system == "Darwin":
        return Path.home() / "Library/Application Support/Cursor/User/workspaceStorage"
    elif system == "Windows":
        appdata = os.getenv('APPDATA')
        if appdata:
            return Path(appdata) / "Cursor/User/workspaceStorage"
        else:
            st.error("Error: APPDATA environment variable not found.")
            return None
    elif system == "Linux":
         config_path = Path.home() / ".config/Cursor/User/workspaceStorage"
         if config_path.exists():
             return config_path
         # Add other potential Linux paths if needed
         st.warning("Warning: Could not automatically determine Cursor storage path on Linux.")
         return None
    else:
        st.error(f"Error: Unsupported operating system: {system}")
        return None

def find_database_files(storage_path):
    """Finds all state.vscdb files within workspace storage subdirectories."""
    db_files = []
    if not storage_path or not storage_path.is_dir():
        # Error already handled by get_cursor_storage_path usually
        return db_files
    try:
        for item in storage_path.iterdir():
            if item.is_dir() and len(item.name) > 10 and item.name != "images":
                 db_path = item / "state.vscdb"
                 if db_path.is_file():
                     db_files.append(db_path)
    except Exception as e:
        st.error(f"Error scanning storage path '{storage_path}': {e}")
    return db_files

def query_chat_data(db_path):
    """Queries a single database file for chat history, parsing the known structure."""
    chats = []
    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        query = """
        SELECT key, value
        FROM ItemTable
        WHERE key = 'workbench.panel.aichat.view.aichat.chatdata'
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        if not rows: return []

        for i, (db_key, row_value) in enumerate(rows):
            try:
                data = json.loads(row_value)
                if not isinstance(data, dict): continue
                tabs = data.get('tabs')
                if not isinstance(tabs, list): continue

                for tab_index, tab_data in enumerate(tabs):
                    if not isinstance(tab_data, dict): continue
                    tab_id = tab_data.get('tabId', f'unknown_tab_{tab_index}')
                    chat_title = tab_data.get('chatTitle', f'Untitled Chat {tab_index}')
                    bubbles = tab_data.get('bubbles')
                    if not isinstance(bubbles, list): continue

                    for bubble_index, bubble_data in enumerate(bubbles):
                        if not isinstance(bubble_data, dict): continue
                        role = bubble_data.get('type', 'unknown')
                        content = bubble_data.get('text')
                        if content is None: continue
                        if role == 'ai': role = 'assistant'
                        content_str = str(content)
                        if content_str.strip() in ('{}', '[]', ''): continue
                        chats.append({
                            "role": str(role),
                            "content": content_str,
                            "tabId": str(tab_id),
                            "chatTitle": str(chat_title),
                            "source_db": db_path.parent.name
                        })
            except json.JSONDecodeError:
                # st.warning(f"Could not decode JSON in {db_path.parent.name} (key: {db_key})")
                pass # Ignore decode errors for now
            except Exception as e:
                 # st.warning(f"Error processing structure in {db_path.parent.name}: {e}")
                 pass # Ignore other processing errors for now

    except sqlite3.OperationalError as e:
        if "no such table: ItemTable" in str(e): pass
        elif "database is locked" in str(e):
             st.warning(f"DB locked: {db_path.parent.name}. Try closing Cursor?")
        else: st.warning(f"SQLite error in {db_path.parent.name}: {e}")
    except Exception as e:
        st.error(f"Failed to read DB {db_path.parent.name}: {e}")

    return chats

@st.cache_data # Cache the data loading process
def load_all_chat_data():
    storage_path = get_cursor_storage_path()
    if not storage_path:
        return None, 0, 0 # Indicate error

    db_files = find_database_files(storage_path)
    if not db_files:
        st.info("No state.vscdb files found in Cursor workspace storage.")
        return {}, 0, 0

    st.write(f"Found {len(db_files)} potential database file(s). Scanning...")

    all_chats = []
    progress_bar = st.progress(0)
    for i, db_path in enumerate(db_files):
        try:
            all_chats.extend(query_chat_data(db_path))
        except Exception as e:
            st.error(f"Error processing {db_path}: {e}")
            st.code(traceback.format_exc())
        progress_bar.progress((i + 1) / len(db_files))

    # Group chats by session (source_db + tabId)
    sessions = defaultdict(list)
    for chat in all_chats:
        session_key = (chat['source_db'], chat['tabId'])
        sessions[session_key].append(chat)

    total_messages = len(all_chats)
    total_sessions = len(sessions)

    return sessions, total_messages, total_sessions

# --- Streamlit App UI ---

st.set_page_config(page_title="Cursor Chat Viewer", layout="wide")
st.title("🔎 Cursor Chat History Viewer")

# Load data using the cached function
with st.spinner("Loading chat history from database files..."):
    sessions_data, total_messages, total_sessions = load_all_chat_data()

if sessions_data is None: # Error during path finding
    st.stop()

st.write(f"Parsed **{total_messages}** messages across **{total_sessions}** unique chat sessions.")

if not sessions_data:
    st.info("No chat sessions found in the scanned databases.")
    st.stop()

# Prepare session list for display
session_list_for_display = []
session_map = {}
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

# Add placeholder option
options = ["-- Select a Chat Session --"] + session_list_for_display

selected_display_name = st.selectbox(
    "Choose a chat session to view:",
    options=options,
    index=0 # Default to placeholder
)

st.divider()

# Display selected chat
if selected_display_name != "-- Select a Chat Session --":
    selected_key = session_map[selected_display_name]
    selected_session_chats = sessions_data[selected_key]

    if selected_session_chats:
        st.header(f"Chat: {selected_session_chats[0].get('chatTitle', 'Untitled Chat')}")
        st.caption(f"Source: {selected_key[0]} | Tab ID: {selected_key[1]}")

        for chat in selected_session_chats:
            role = chat.get('role', 'unknown')
            # Ensure role is one of the types st.chat_message expects, default to "assistant"
            if role not in ["user", "assistant"]:
                role = "assistant"
            with st.chat_message(role):
                st.markdown(chat.get('content', '[No Content]')) # Use markdown to render content (handles code blocks)
    else:
        st.write("This session appears to have no messages.")
else:
    st.info("Select a chat session from the dropdown above to view its messages.") 