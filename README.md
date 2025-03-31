# Cursor Chat Viewer

Tools to view and search your local Cursor chat history and recently opened files.

**Core Logic (`chat_utils.py`)**

Both the terminal and web UI viewers now share core logic for finding databases and parsing data, which is located in `chat_utils.py`.

## Option 1: Interactive Terminal Viewer (`cursor_chat_viewer.py`)

A simple Python script to find, display, and interactively select your local Cursor chat history and view recent file history across different workspaces directly in the terminal.

### Features

- Automatically detects Cursor's data directory on macOS, Windows, and Linux (common paths).
- Scans all workspace storage folders for databases (`state.vscdb`).
- Extracts chat history stored under the `workbench.panel.aichat.view.aichat.chatdata` key.
- **Extracts recently opened file history** stored under the `history.entries` key.
- Parses the JSON data structures.
- Presents an interactive numbered list of chat sessions (tabs) with titles and message counts.
- Displays the full conversation for the selected session.
- **Optionally displays the recent file history** for the workspace associated with the selected chat session.

### Prerequisites

- **Python 3:** Ensure you have Python 3 installed.
- **Cursor:** Reads data from a local Cursor installation.
- **Project Files:** Requires `cursor_chat_viewer.py` and `chat_utils.py` in the same directory.

### Usage

1.  **Save the scripts:** Ensure `cursor_chat_viewer.py` and `chat_utils.py` are saved in the same directory.
2.  **Open your terminal:**
    - On macOS: `Terminal.app`.
    - On Windows: `Command Prompt` or `PowerShell`.
    - On Linux: Your preferred terminal emulator.
3.  **Navigate to the script's directory:**
    ```bash
    cd path/to/your/script
    ```
4.  **Run the script:**
    ```bash
    python cursor_chat_viewer.py
    # or
    python3 cursor_chat_viewer.py
    ```
5.  **Interact:** Follow the prompts to enter the number of the chat session you want to view, or `0` to exit. After viewing a chat, it may prompt you to view the associated file history.

## Option 2: Web UI Viewer (`cursor_chat_streamlit.py`)

A web-based interface built with Streamlit to browse your chat history and view recent file history.

### Features

- Uses the same shared data detection and parsing logic from `chat_utils.py`.
- Provides a user-friendly web interface.
- Uses caching (`@st.cache_data`) for faster reloading after the initial scan.
- Displays chat sessions in a dropdown menu.
- Renders the selected conversation using Streamlit's chat elements (`st.chat_message`).
- **Displays recent file history** in an expandable section below the selected chat.
- Handles cases where only file history might be available for some workspaces.

### Prerequisites

- **Python 3 & pip:** Ensure you have Python 3 and pip installed.
- **Cursor:** Reads data from a local Cursor installation.
- **Project Files:** Requires `cursor_chat_streamlit.py`, `chat_utils.py`, and `requirements.txt` in the same directory.

### Usage

1.  **Save the scripts:** Ensure `cursor_chat_streamlit.py`, `chat_utils.py`, and `requirements.txt` are saved in the same directory.
2.  **Open your terminal** and navigate to that directory.
3.  **Create & Activate Virtual Environment (Recommended):**
    ```bash
    # Create a virtual environment (e.g., named .venv)
    python3 -m venv .venv
    # Activate it
    # On macOS/Linux:
    source .venv/bin/activate
    # On Windows:
    # .\venv\Scripts\activate
    ```
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Run the Streamlit app:**
    ```bash
    streamlit run cursor_chat_streamlit.py
    ```
6.  **Interact:** Streamlit will provide a local URL (usually `http://localhost:8501`). Open this in your web browser. Use the dropdown to select and view chat sessions and expand the section below to see file history.

## How it Works (Both Options)

The scripts locate the `workspaceStorage` directory used by Cursor using `chat_utils.py`. They iterate through subdirectories, looking for `state.vscdb` files. These SQLite database files contain various pieces of state data stored as JSON strings in the `ItemTable` table.

The shared logic in `chat_utils.py` connects to each database, executes SQL queries to fetch values for specific keys (`workbench.panel.aichat.view.aichat.chatdata` for chats, `history.entries` for file history), parses the JSON, extracts the relevant information (messages, file paths), and returns structured data.

The individual scripts (`cursor_chat_viewer.py` and `cursor_chat_streamlit.py`) then use this data to present it either in the terminal or via the Streamlit web UI.

## Troubleshooting

- **`No state.vscdb files found` / `No chat sessions or file history found`:** Ensure Cursor has been run and has saved data. Double-check the `workspaceStorage` path detection if using a non-standard location (you might need to edit the path in the `get_cursor_storage_path` function within `chat_utils.py`).
- **Database Locked Warnings:** Try closing Cursor completely before running the scripts, as Cursor might keep the database files locked while it's running.
- **Permission Errors (Windows):** You might need to run your terminal as an administrator.
- **Streamlit Import Error:** Make sure you have installed the requirements using `pip install -r requirements.txt` (ideally within a virtual environment).
- **JSON/Structure Errors:** If you encounter new errors after a Cursor update, the internal data structure (keys like `workbench.panel.aichat.view.aichat.chatdata` or `history.entries`, or their JSON format) might have changed, requiring updates to the parsing logic in `chat_utils.py`.
- **ImportError: No module named 'chat_utils'**: Ensure `chat_utils.py` is in the same directory as the script you are trying to run (`cursor_chat_viewer.py` or `cursor_chat_streamlit.py`).
