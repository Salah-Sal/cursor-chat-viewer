import os
import sqlite3
import json
import platform
import argparse
from pathlib import Path
from collections import defaultdict

def get_cursor_storage_path():
    """Determines the path to Cursor's workspaceStorage based on the OS."""
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / "Library/Application Support/Cursor/User/workspaceStorage"
    elif system == "Windows":
        appdata = os.getenv('APPDATA')
        if appdata:
            return Path(appdata) / "Cursor/User/workspaceStorage"
        else:
            # Fallback or error handling if APPDATA is not set
            print("Error: APPDATA environment variable not found.")
            return None
    elif system == "Linux":
         # Typical path on Linux, adjust if necessary for your setup
         # Check common locations: ~/.config/Cursor or ~/.cursor
         config_path = Path.home() / ".config/Cursor/User/workspaceStorage"
         if config_path.exists():
             return config_path
         # Add other potential Linux paths if needed
         print("Warning: Could not automatically determine Cursor storage path on Linux.")
         print("Please update the script with the correct path for your system.")
         return None # Or prompt user, or use a default guess
    else:
        print(f"Error: Unsupported operating system: {system}")
        return None

def find_database_files(storage_path):
    """Finds all state.vscdb files within workspace storage subdirectories."""
    db_files = []
    if not storage_path or not storage_path.is_dir():
        print(f"Error: Storage path '{storage_path}' not found or is not a directory.")
        return db_files

    for item in storage_path.iterdir():
        # Check if it's a directory (potential workspace folder)
        # We assume workspace folders have longer names (like hashes)
        # or are not known directories like 'images'. Adjust if needed.
        if item.is_dir() and len(item.name) > 10 and item.name != "images": # Basic filter
             db_path = item / "state.vscdb"
             if db_path.is_file():
                 db_files.append(db_path)
    return db_files

def query_chat_data(db_path):
    """Queries a single database file for chat history, parsing the known structure with lenient handling for missing bubble fields."""
    chats = []
    processed_rows = 0
    processed_messages = 0
    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        # Focus only on the key that seems to contain the full chat data
        query = """
        SELECT key, value
        FROM ItemTable
        WHERE key = 'workbench.panel.aichat.view.aichat.chatdata'
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        if not rows: return [] # Key not found

        for i, (db_key, row_value) in enumerate(rows):
            try:
                data = json.loads(row_value)
                processed_rows += 1

                if not isinstance(data, dict):
                    # print(f"DEBUG: Row {i+1} (key: {db_key}) - Unexpected data type: {type(data)}, expected dict.")
                    continue

                tabs = data.get('tabs')
                if not isinstance(tabs, list):
                    # print(f"DEBUG: Row {i+1} (key: {db_key}) - 'tabs' key missing or not a list.")
                    continue

                for tab_index, tab_data in enumerate(tabs):
                    if not isinstance(tab_data, dict): continue

                    tab_id = tab_data.get('tabId', f'unknown_tab_{tab_index}')
                    chat_title = tab_data.get('chatTitle', f'Untitled Chat {tab_index}')
                    bubbles = tab_data.get('bubbles')

                    if not isinstance(bubbles, list): continue

                    for bubble_index, bubble_data in enumerate(bubbles):
                        if not isinstance(bubble_data, dict): continue

                        # --- Use 'text' key instead of 'message' --- 
                        role = bubble_data.get('type', '[Missing Role]') 
                        content = bubble_data.get('text') # Get content from 'text' key
                        
                        # Skip bubble if content is missing (None) 
                        if content is None:
                            # No need to print debug anymore, just skip
                            continue 
                        
                        # Adjust role names for clarity
                        if role == 'ai': role = 'assistant'
                        
                        # Ensure content is string
                        content_str = str(content)
                        
                        # Skip bubbles if content string is effectively empty
                        if content_str.strip() in ('{}', '[]', ''):
                            continue

                        chats.append({
                            "role": str(role),
                            "content": content_str,
                            "tabId": str(tab_id),
                            "chatTitle": str(chat_title),
                            "source_db": db_path.parent.name
                        })
                        processed_messages += 1
                        # --- End Lenient Extraction ---

            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from row {i+1} (key: {db_key}) in {db_path.parent.name}")
            except Exception as e:
                 print(f"Warning: Error processing row {i+1} (key: {db_key}) structure in {db_path.parent.name}: {e}")

    except sqlite3.OperationalError as e:
        if "no such table: ItemTable" in str(e):
             pass
        elif "database is locked" in str(e):
             print(f"Warning: Database locked, skipping: {db_path}. Try closing Cursor?")
        elif "malformed" in str(e) or "unsupported file format" in str(e):
             print(f"Warning: Database file might be corrupt or invalid, skipping: {db_path}")
        else:
            print(f"Warning: SQLite error querying {db_path}: {e}")
    except Exception as e:
        print(f"Error: Could not connect to or read {db_path}: {e}")

    return chats

def display_session(session_chats):
    """Displays the messages for a selected chat session."""
    if not session_chats:
        print("No messages found for this session.")
        return

    # Assume all chats in the list are from the same session
    title = session_chats[0].get('chatTitle', 'Untitled Chat')
    source = session_chats[0].get('source_db', 'unknown_source')
    tab_id = session_chats[0].get('tabId', 'unknown_tab')

    print(f"\n--- Chat: {title} (Tab: {tab_id}, Source: {source}) ---")
    for chat in session_chats:
        role = chat.get('role', 'unknown').capitalize()
        content = chat.get('content', '').strip()
        print(f"[{role}]: {content}\n")
    print("-" * 50)

def main():
    parser = argparse.ArgumentParser(description="Interactively view Cursor chat history.")
    # Keep search as an option, but we'll apply it *after* session selection for now
    # parser.add_argument("-s", "--search", type=str, help="Keyword to search for in chat messages (case-insensitive).")
    args = parser.parse_args()

    storage_path = get_cursor_storage_path()
    if not storage_path:
        return

    print(f"Scanning for databases in: {storage_path}")
    db_files = find_database_files(storage_path)

    if not db_files:
        print("No state.vscdb files found.")
        return

    print(f"Found {len(db_files)} potential database(s). Querying...")

    all_chats = []
    for db_path in db_files:
        all_chats.extend(query_chat_data(db_path))

    print(f"Total messages parsed: {len(all_chats)}")

    if not all_chats:
        print("No chat messages found in any database.")
        return

    # Group chats by session (source_db + tabId)
    sessions = defaultdict(list)
    for chat in all_chats:
        session_key = (chat['source_db'], chat['tabId'])
        sessions[session_key].append(chat)

    print(f"Found {len(sessions)} unique chat sessions.")

    # Prepare list for display
    session_list = []
    for (source_db, tab_id), chats in sessions.items():
        if chats: # Ensure there are messages
            title = chats[0].get('chatTitle', 'Untitled Chat')
            num_messages = len(chats)
            session_list.append({
                'key': (source_db, tab_id),
                'title': title,
                'source': source_db,
                'messages_count': num_messages,
                'chats': chats # Keep the actual chats associated
            })

    # Sort sessions for consistent display (e.g., by source then title)
    session_list.sort(key=lambda s: (s['source'], s['title']))

    print("\nPlease select a chat session to view:")
    print("-" * 50)
    for i, session_info in enumerate(session_list):
        print(f" {i+1}: {session_info['title']} ({session_info['messages_count']} messages) [Source: {session_info['source']}]")
    print(" 0: Exit")
    print("-" * 50)

    while True:
        try:
            choice = input("Enter session number (or 0 to exit): ")
            choice_num = int(choice)

            if choice_num == 0:
                print("Exiting.")
                break
            elif 1 <= choice_num <= len(session_list):
                selected_session_chats = session_list[choice_num - 1]['chats']
                display_session(selected_session_chats)
                # Optionally add search within the selected session here later
                print("\nSelect another session or 0 to exit.")
            else:
                print(f"Invalid choice. Please enter a number between 0 and {len(session_list)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nExiting.")
            break

if __name__ == "__main__":
    main() 