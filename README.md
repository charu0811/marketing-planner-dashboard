# Wylth — Marketing Task Manager (Streamlit Dashboard)

A Streamlit-based marketing task manager with SQLite persistence.

## Setup & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run app.py
```

## Features

- **Board View**: Kanban-style columns (To Do, In Progress, Done, Carryforward, Blocked)
- **List View**: Chronological table grouped by week
- **Week Navigation**: Browse tasks by week, go to current week, or show all
- **Filters**: Search, owner, status, approval, platform
- **CRUD**: Create, edit, delete tasks with full metadata
- **UTM Link Builder**: Generate tracked URLs with utm parameters
- **SQLite Storage**: All data persists in `tasks.db`
- **Seed Data**: Pre-populated with completed tasks from the original spreadsheet

## Hosting on Streamlit Community Cloud

1. Push this folder to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set the main file to `app.py`
5. Deploy!

> Note: On Streamlit Cloud, SQLite data resets on redeploy. For persistent cloud storage, consider connecting to a hosted database or using st.session_state with a cloud DB.

## File Structure

- `app.py` — Main Streamlit application
- `database.py` — SQLite database layer (CRUD operations)
- `requirements.txt` — Python dependencies
- `tasks.db` — SQLite database (auto-created on first run)
