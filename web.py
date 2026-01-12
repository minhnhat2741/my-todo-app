import streamlit as st
import functions
import hashlib


st.title("Apotek assistent")
st.subheader("Ting å gjøre på apotek")
st.write("""Appen som hjelper deg å ungå hodepine""")



def add_todo():
    todo = st.session_state["new_todo"].strip()
    if not todo:
        return
    todos = functions.get_todos()
    todos.append(todo + "\n")
    functions.write_todos(todos)
    st.session_state["new_todo"] = "" # clear input

# always read fresh on each rerun
todos = functions.get_todos()

delete_line = None


for i, line in enumerate(todos):
    text = line.strip()
    key = hashlib.md5(f"{i}:{line}".encode()).hexdigest()
    if st.checkbox(text, key=key):
        delete_line = i

if delete_line is not None:
    todos.pop(delete_line)
    functions.write_todos(todos)
    st.rerun()

st.text_input(label="", placeholder="Add something", on_change=add_todo, key="new_todo")
