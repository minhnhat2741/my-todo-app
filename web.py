import streamlit as st
import functions

st.title("Apotek assistent")
st.subheader("Ting å gjøre på apotek")
st.write("""Appen som hjelper deg å ungå hodepine""")

#todos = functions.get_todos()

def add_todo():
    todo = st.session_state["new_todo"].strip()
    if not todo:
        return
    todos.append(todo + "\n")

    functions.write_todos(todos)
    st.session_state["new_todo"] = "" # clear input

# always read fresh on each rerun
todos = functions.get_todos()


for index, todo in enumerate(todos):
    clean = todo.strip()
    checkbox = st.checkbox(clean, key=f"todo_{index}")
    if checkbox:
        todos.pop(index)
        functions.write_todos(todos)

        st.rerun()

st.text_input(label="", placeholder="Add something", on_change=add_todo, key="new_todo")
