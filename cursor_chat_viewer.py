import os
# import sqlite3 # No longer needed directly here
# import json # No longer needed directly here
import platform
import argparse
from pathlib import Path
from collections import defaultdict
import chat_utils # Add this line near the top

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

    # Remove the old loading logic (get_storage_path, find_database_files, loop)
    try:
        all_sessions, all_file_histories = chat_utils.load_all_workspace_data()
    except FileNotFoundError as e:
         print(f"Error: {e}")
         return
    except Exception as e:
         print(f"An unexpected error occurred during data loading: {e}")
         # Consider adding traceback print here for debugging if needed
         # import traceback
         # print(traceback.format_exc())
         return

    total_messages = sum(len(chats) for chats in all_sessions.values()) # Calculate total messages
    print(f"Total messages parsed: {total_messages}") # Use calculated total
    print(f"Found file history for {len(all_file_histories)} workspaces.")

    if not all_sessions and not all_file_histories: # Check if anything was found
        print("No chat sessions or file history found in any database.")
        return

    # Group chats by session (source_db + tabId) -> This is now done by load_all_workspace_data
    # sessions = defaultdict(list)
    # for chat in all_chats:
    #     session_key = (chat['source_db'], chat['tabId'])
    #     sessions[session_key].append(chat)

    # Use all_sessions directly
    print(f"Found {len(all_sessions)} unique chat sessions.")

    # Prepare list for display
    session_list = []
    # Use all_sessions which is already grouped: key=(workspace_id, tabId), value=list_of_chats
    for (source_db, tab_id), chats in all_sessions.items():
        if chats: # Ensure there are messages
            title = chats[0].get('chatTitle', 'Untitled Chat')
            num_messages = len(chats)
            session_list.append({
                'key': (source_db, tab_id),
                'title': title,
                'source': source_db, # workspace_id
                'messages_count': num_messages,
                'chats': chats # Keep the actual chats associated
            })

    # Sort sessions for consistent display (e.g., by source then title)
    session_list.sort(key=lambda s: (s['source'], s['title']))

    # Only print menu if there are sessions to choose from
    if session_list:
        print("\nPlease select a chat session to view:")
        print("-" * 50)
        for i, session_info in enumerate(session_list):
            print(f" {i+1}: {session_info['title']} ({session_info['messages_count']} messages) [Source: {session_info['source']}]")
        print(" 0: Exit")
        print("-" * 50)
    elif all_file_histories: # Handle case with history but no chats
        print("\nNo chat sessions found.")
        # Offer to view history directly (optional enhancement)
        # For now, just exit if no chats to select.
        print("Exiting as there are no chat sessions to display.")
        return
    else: # Should have been caught earlier
        print("Error: No data loaded.")
        return

    while True:
        try:
            choice = input("Enter session number (or 0 to exit): ")
            choice_num = int(choice)

            if choice_num == 0: # Exit
                 print("Exiting.")
                 break
            elif 1 <= choice_num <= len(session_list):
                selected_session_info = session_list[choice_num - 1]
                selected_session_chats = selected_session_info['chats']
                workspace_id = selected_session_info['source'] # Get workspace ID

                display_session(selected_session_chats) # Show chat

                # --- Add File History Option ---
                # Only ask if history exists for this workspace
                if workspace_id in all_file_histories:
                    history_choice = input(f"Show file history for workspace '{workspace_id}'? (y/n): ").lower()
                    if history_choice == 'y':
                        history = all_file_histories.get(workspace_id)
                        if history:
                            print(f"\n--- File History for {workspace_id} ---")
                            # Show unique entries, maybe newest first?
                            unique_history = list(dict.fromkeys(history))
                            print(f"({len(unique_history)} unique files found)")
                            for i, filepath in enumerate(reversed(unique_history)):
                                print(f" {i+1}: {filepath}")
                            print("-" * 50)
                        # else case shouldn't happen due to check above, but good practice:
                        # else:
                        #    print(f"No file history found for workspace '{workspace_id}'.")
                else:
                     print(f"(No file history found for workspace '{workspace_id}'.)")
                # --- End File History Option ---

                print("\nSelect another chat session or 0 to exit.")
            else:
                print(f"Invalid choice. Please enter a number between 0 and {len(session_list)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nExiting.")
            break

if __name__ == "__main__":
    main() 