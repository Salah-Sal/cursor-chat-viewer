import os
import platform
from pathlib import Path
import sqlite3
import json
from collections import defaultdict
import traceback

def parse_chat_data_from_json(data, workspace_id):
    """Parses chat data from a loaded JSON structure for a given workspace."""
    chats = []
    # Start directly with checking the loaded data structure
    if not isinstance(data, dict): 
        # print(f"Debug (parse_chat_data): Expected dict, got {type(data)} for workspace {workspace_id}")
        return chats # Expect a dict at the top level

    tabs = data.get('tabs')
    if not isinstance(tabs, list):
        # print(f"Debug (parse_chat_data): No 'tabs' list found in workspace {workspace_id}")
        return chats

    # Keep the loops for tabs and bubbles
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
                # Use workspace_id instead of db_path.parent.name
                "source_db": str(workspace_id) 
            })

    # No database operations here, so associated error handling is removed.
    # Errors related to JSON structure (KeyError, TypeError) will be caught
    # by the calling function (load_all_workspace_data)
    return chats

def get_cursor_storage_path():
    """Determines the path to Cursor's workspaceStorage based on the OS."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library/Application Support/Cursor/User/workspaceStorage"
    elif system == "Windows":
        appdata = os.getenv('APPDATA')
        if appdata:
            return Path(appdata) / "Cursor/User/workspaceStorage"
        else:
            # print("Error (chat_utils): APPDATA environment variable not found.")
            return None # Just return None
    elif system == "Linux":
         config_path = Path.home() / ".config/Cursor/User/workspaceStorage"
         if config_path.exists():
             return config_path
         # Add other potential Linux paths if needed
         # print("Warning (chat_utils): Could not automatically determine Cursor storage path on Linux.")
         return None # Just return None
    else:
        # print(f"Error (chat_utils): Unsupported operating system: {system}")
        return None # Unsupported OS

def find_database_files(storage_path):
    """Finds all state.vscdb files within workspace storage subdirectories."""
    db_files = []
    if not storage_path or not storage_path.is_dir():
        # Error should be handled by the caller checking the result of get_cursor_storage_path
        return db_files 
    try:
        for item in storage_path.iterdir():
            if item.is_dir() and len(item.name) > 10 and item.name != "images":
                 db_path = item / "state.vscdb"
                 if db_path.is_file():
                     db_files.append(db_path)
    except Exception as e:
        print(f"Error (chat_utils): Error scanning storage path '{storage_path}': {e}") # Use print
    return db_files 

def parse_file_history(json_data):
    """Parses the JSON structure expected for the 'history.entries' key."""
    files = []
    if not isinstance(json_data, list):
        # print("Debug (parse_file_history): Expected list, got:", type(json_data))
        return files # Expect a list of entries

    for entry in json_data:
        if isinstance(entry, dict):
            resource_uri = entry.get('editor', {}).get('resource')
            if isinstance(resource_uri, str) and resource_uri.startswith('file:///'):
                # Clean up the URI to be a more readable path
                file_path = resource_uri[7:] # Remove 'file:///'
                # Optional: Decode URL encoding if needed (e.g., spaces as %20)
                # from urllib.parse import unquote
                # file_path = unquote(file_path)
                files.append(file_path)
    return files

def query_keys_from_db(db_path, keys_to_query: list):
    """Queries a specific list of keys from the ItemTable and returns their raw values."""
    data = {key: None for key in keys_to_query} # Initialize results dict
    try:
        # Use mode=ro for read-only access
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        # Create placeholders for the query
        placeholders = ','.join('?' for key in keys_to_query)
        query = f"SELECT key, value FROM ItemTable WHERE key IN ({placeholders})"
        cursor.execute(query, keys_to_query)
        rows = cursor.fetchall()
        conn.close()

        for key, value in rows:
            if key in data:
                data[key] = value # Store the raw BLOB/text value

    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print(f"Warning (chat_utils): DB locked: {db_path.parent.name}.")
        elif "no such table" in str(e):
             pass # Ignore if table doesn't exist
        else:
             print(f"Warning (chat_utils): SQLite error querying keys in {db_path.parent.name}: {e}")
    except Exception as e:
        print(f"Error (chat_utils): Failed to query keys from DB {db_path.parent.name}: {e}")

    return data # Return dict with raw values (or None if key not found/error) 

# Note: @st.cache_data should be applied in the Streamlit script, not here.
def load_all_workspace_data():
    """Loads both chat history and file history from all found databases."""
    storage_path = get_cursor_storage_path()
    if not storage_path:
        # Raise an error or return a specific indicator
        raise FileNotFoundError("Could not determine Cursor storage path.")

    if not storage_path.is_dir(): # Check if path exists before finding files
         raise FileNotFoundError(f"Storage path '{storage_path}' not found or is not a directory.")

    db_files = find_database_files(storage_path)
    if not db_files:
        print("Info (chat_utils): No state.vscdb files found.")
        return {}, {} # Return empty dicts for sessions and history

    print(f"Info (chat_utils): Found {len(db_files)} potential database file(s). Scanning...")

    all_sessions = defaultdict(list)
    all_file_histories = defaultdict(list)
    keys_to_find = [
        'workbench.panel.aichat.view.aichat.chatdata', # Key for chat data
        'history.entries'                             # Key for file history
    ]

    for db_path in db_files:
        workspace_id = db_path.parent.name # Get the workspace folder name
        raw_data = query_keys_from_db(db_path, keys_to_find)

        # Process Chat Data
        chat_raw_value = raw_data.get('workbench.panel.aichat.view.aichat.chatdata')
        if chat_raw_value:
            try:
                chat_json = json.loads(chat_raw_value)
                # Call the refactored parsing function
                parsed_chats = parse_chat_data_from_json(chat_json, workspace_id)

                # Group chats by session (source_db/workspace_id + tabId)
                for chat in parsed_chats:
                    session_key = (chat['source_db'], chat['tabId']) # source_db is workspace_id
                    all_sessions[session_key].append(chat)

            except json.JSONDecodeError:
                print(f"Warning (chat_utils): Could not decode chat JSON in {workspace_id}")
            except Exception as e:
                print(f"Warning (chat_utils): Error processing chat structure in {workspace_id}: {e}")
                # print(traceback.format_exc()) # Uncomment for detailed debugging

        # Process File History Data
        history_raw_value = raw_data.get('history.entries')
        if history_raw_value:
            try:
                history_json = json.loads(history_raw_value)
                parsed_files = parse_file_history(history_json)
                if parsed_files:
                    # Store history keyed by workspace_id
                    all_file_histories[workspace_id].extend(parsed_files)
                    # Optional: Remove duplicates if needed
                    # all_file_histories[workspace_id] = list(dict.fromkeys(all_file_histories[workspace_id]))
            except json.JSONDecodeError:
                print(f"Warning (chat_utils): Could not decode file history JSON in {workspace_id}")
            except Exception as e:
                 print(f"Warning (chat_utils): Error processing file history structure in {workspace_id}: {e}")
                 # print(traceback.format_exc()) # Uncomment for detailed debugging

    total_messages = sum(len(chats) for chats in all_sessions.values())
    total_sessions = len(all_sessions)
    print(f"Info (chat_utils): Parsed {total_messages} messages across {total_sessions} unique chat sessions.")
    print(f"Info (chat_utils): Parsed file history for {len(all_file_histories)} workspaces.")

    # Return both sets of data, grouped appropriately
    return all_sessions, all_file_histories 