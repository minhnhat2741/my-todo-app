import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


st.set_page_config(page_title="Todo App", page_icon="✅")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    return gspread.authorize(creds)

def get_sheet():
    gc = get_client()
    sh = gc.open_by_url(st.secrets["gsheet"]["spreadsheet_url"])
    ws = sh.worksheet(st.secrets["gsheet"]["worksheet"])
    return ws

def read_todos():
    ws = get_sheet()
    values = ws.get_all_values()
    if not values:
        return []
    # values[0] is header row
    rows = values[1:]
    return [r[0] for r in rows if r and r[0].strip()]

def add_todo_to_sheet(text: str):
    ws = get_sheet()
    ws.append_row([text])

def delete_todo_from_sheet(todo_text: str):
    # Deletes first matching row (simple approach)
    ws = get_sheet()
    col = ws.col_values(1)  # includes header
    for idx, val in enumerate(col[1:], start=2):  # start=2 because row 1 header
        if val == todo_text:
            ws.delete_rows(idx)
            return


# App lay out
st.title("✅ ApotekHjelper")
st.subheader("⚠️ Ingen personopplysninger oppgis her")


def add_todo():
    text = st.session_state.new_todo.strip()
    if not text:
        return
    add_todo_to_sheet(text)
    st.session_state.new_todo = ""
    #st.rerun()

st.text_input("", placeholder="Add something…", key="new_todo", on_change=add_todo)

todos = read_todos()

if not todos:
    st.info("No todos yet. Add one above 👆")
else:
    for todo in todos:
        c1, c2 = st.columns([0.85, 0.15])
        with c1:
            st.write(todo)
        with c2:
            if st.button("🗑️ Delete", key=f"del_{todo}"):
                delete_todo_from_sheet(todo)
                st.rerun()








