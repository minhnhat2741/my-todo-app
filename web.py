import streamlit as st
from gsheets import get_worksheet

st.set_page_config(page_title="Todo App", page_icon="✅")

# ---------- LOGIN ----------
def login_page():
    st.title("🔐 Login")
    st.caption("Enter the password to access the app.")
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

require_login()

# ---------- SIDEBAR: link ABOVE logout ----------
#st.sidebar.header("Menu")

st.sidebar.divider()

if st.sidebar.button("Log out"):
    st.session_state["logged_in"] = False
    st.rerun()


# ---------- TODO APP (DEFAULT) ----------
st.title("✅ ApotekHjelper")
st.subheader("⚠️ Ingen personopplysninger oppgis her")

WS = get_worksheet(
    st.secrets["gsheet"]["spreadsheet_url"],
    st.secrets["gsheet"]["worksheet"],  # "todos"
)

def read_todos():
    values = WS.get_all_values()
    if not values:
        return []
    rows = values[1:]  # skip header
    return [r[0] for r in rows if r and r[0].strip()]

def add_todo():
    text = st.session_state.new_todo.strip()
    if not text:
        return
    WS.append_row([text])
    st.session_state.new_todo = ""  # callback reruns automatically

def delete_todo(todo_text: str):
    col = WS.col_values(1)  # includes header
    for idx, val in enumerate(col[1:], start=2):
        if val == todo_text:
            WS.delete_rows(idx)
            st.rerun()
            return

st.text_input("", placeholder="Add something…", key="new_todo", on_change=add_todo)
st.divider()

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
                delete_todo(todo)
