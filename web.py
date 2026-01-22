import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


st.set_page_config(page_title="Todo App", page_icon="✅")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# -- AUTH --
def login_page():
    st.title("🔐 Login")
    st.caption("Enter the password to access the Todo App.")

    pw = st.text_input("Password", type="password")

    if st.button("Log in", type="primary"):
        if pw == st.secrets["auth"]["password"]:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Wrong password")


def require_login():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if not st.session_state["logged_in"]:
        login_page()
        st.stop()


# -- GOOGLE SHEET --
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


# -- APP LAY OUT --



def add_todo():
    text = st.session_state.new_todo.strip()
    if not text:
        return
    add_todo_to_sheet(text)
    st.session_state.new_todo = ""
    #st.rerun()

st.text_input("", placeholder="Add something…", key="new_todo", on_change=add_todo)


# -- RUN APP --
def todo_app():
    st.title("✅ ApotekHjelper")
    st.subheader("⚠️ Ingen personopplysninger oppgis her")

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
    st.sidebar.divider()
    if st.sidebar.button("Log out"):
        st.session_state["logged_in"] = False
        st.rerun()

# -- RUN --
require_login()
todo_app()







