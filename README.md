# Cursor Chat Viewer

Tools to view and search your local Cursor chat history.

## Option 1: Interactive Terminal Viewer (`cursor_chat_viewer.py`)

A simple Python script to find, display, and interactively select your local Cursor chat history across different workspaces directly in the terminal.

### Features

- Automatically detects Cursor's data directory on macOS, Windows, and Linux (common paths).
- Scans all workspace storage folders for chat databases (`state.vscdb`).
- Extracts chat history stored under the `workbench.panel.aichat.view.aichat.chatdata` key.
- Parses the JSON chat data (handles `tabs` -> `bubbles` structure, uses `text` key).
- Presents an interactive numbered list of chat sessions (tabs) with titles and message counts.
- Displays the full conversation for the selected session.

### Prerequisites

- **Python 3:** Ensure you have Python 3 installed.
- **Cursor:** Reads data from a local Cursor installation.

### Usage

1.  **Save the script:** Ensure `cursor_chat_viewer.py` is saved.
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
5.  **Interact:** Follow the prompts to enter the number of the chat session you want to view, or `0` to exit.

## Option 2: Web UI Viewer (`cursor_chat_streamlit.py`)

A web-based interface built with Streamlit to browse your chat history.

### Features

- Uses the same data detection and parsing logic as the terminal viewer.
- Provides a user-friendly web interface.
- Uses caching (`@st.cache_data`) for faster reloading after the initial scan.
- Displays chat sessions in a dropdown menu.
- Renders the selected conversation using Streamlit's chat elements (`st.chat_message`).

### Prerequisites

- **Python 3 & pip:** Ensure you have Python 3 and pip installed.
- **Cursor:** Reads data from a local Cursor installation.

### Usage

1.  **Save the scripts:** Ensure `cursor_chat_streamlit.py` and `requirements.txt` are saved in the same directory.
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
6.  **Interact:** Streamlit will provide a local URL (usually `http://localhost:8501`). Open this in your web browser. Use the dropdown to select and view chat sessions.

## How it Works (Both Options)

The scripts locate the `workspaceStorage` directory used by Cursor. They iterate through subdirectories, looking for `state.vscdb` files. These SQLite database files contain chat history stored as JSON strings in the `ItemTable` table under the `workbench.panel.aichat.view.aichat.chatdata` key.

The scripts connect to each database, execute a SQL query, parse the JSON, extract messages (`type` and `text` from bubbles within tabs), and present them either in the terminal or via the Streamlit web UI.

## Troubleshooting

- **`No state.vscdb files found` / `No chat sessions found`:** Ensure Cursor has been run and has saved data. Double-check the `workspaceStorage` path detection if using a non-standard location (you might need to edit the path in the `get_cursor_storage_path` function).
- **Database Locked Warnings:** Try closing Cursor completely before running the scripts, as Cursor might keep the database files locked while it's running.
- **Permission Errors (Windows):** You might need to run your terminal as an administrator.
- **Streamlit Import Error:** Make sure you have installed the requirements using `pip install -r requirements.txt` (ideally within a virtual environment).
- **JSON/Structure Errors:** If you encounter new errors after a Cursor update, the internal data structure might have changed, requiring updates to the parsing logic in the `query_chat_data` function.
