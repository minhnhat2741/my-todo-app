from pathlib import Path

FILEPATH = Path("todos.txt")

def get_todos(filepath=FILEPATH):

    """Read a text file and return a list of todos (lines) """
    filepath = Path(filepath)
    if not filepath.exists():
        filepath.write_text('')
        return []
    #with open(filepath, "r") as file_local:
    #    todos_local = file_local.readlines()

    return filepath.read_text().splitlines(keepends=True)

def write_todos( todos_arg, filepath=FILEPATH):
    """ Write the list of todos (lines) to a text file """
    with open(filepath, "w") as file:
        file.writelines(todos_arg)


if __name__ == "__main__":
    print("hello world")

