import pytest

from maieutik import cli, tools as tl
from maieutik import progress as prog

REFERENCE_SOLUTION = '''\
def add_task(tasks, title):
    task = {"id": len(tasks) + 1, "title": title, "done": False}
    tasks.append(task)
    return task


def complete_task(tasks, task_id):
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = True
            return task
    raise KeyError(task_id)


def list_tasks(tasks, only_open=False):
    return [t for t in tasks if not (only_open and t["done"])]
'''


def test_projects_are_listed():
    assert "todo-api" in cli.list_projects()


def test_init_copies_the_project_and_records_it(tmp_path):
    created = cli.init_workspace(tmp_path / "mon-projet")

    names = {path.name for path in created}
    assert {"PROJECT.md", "test_step1_tasks.py"} <= names
    assert prog.load(tmp_path / "mon-projet")["project"] == "todo-api"


def test_init_never_overwrites_existing_files(tmp_path):
    (tmp_path / "PROJECT.md").write_text("mes notes", encoding="utf-8")

    cli.init_workspace(tmp_path)

    assert (tmp_path / "PROJECT.md").read_text(encoding="utf-8") == "mes notes"


def test_init_keeps_existing_progress(tmp_path):
    data = prog.empty_progress()
    prog.update_profile(data, level="intermédiaire", project="autre")
    prog.save(tmp_path, data)

    cli.init_workspace(tmp_path)

    loaded = prog.load(tmp_path)
    assert (loaded["level"], loaded["project"]) == ("intermédiaire", "autre")


def test_init_rejects_unknown_project(tmp_path):
    with pytest.raises(SystemExit):
        cli.init_workspace(tmp_path, "inconnu")


def test_starter_tests_fail_then_pass_with_a_reference_solution(tmp_path):
    cli.init_workspace(tmp_path)

    assert "failed" in tl.run_tests(tmp_path) or "error" in tl.run_tests(tmp_path).lower()

    (tmp_path / "todo.py").write_text(REFERENCE_SOLUTION, encoding="utf-8")

    assert "5 passed" in tl.run_tests(tmp_path)


def test_slash_commands_are_translated():
    assert cli.translate_input("/indice").startswith("[INDICE]")
    assert cli.translate_input("/tests").startswith("[TESTS]")
    assert cli.translate_input("/relis").startswith("[RELECTURE]")
    assert cli.translate_input("/explique les listes") == (
        "[MODE EXPLIQUE-MOI] Explique-moi le pourquoi : les listes"
    )
    assert cli.translate_input("/explique").startswith("[MODE EXPLIQUE-MOI]")


def test_plain_text_is_left_untouched():
    assert cli.translate_input("  comment faire une boucle ?  ") == "comment faire une boucle ?"


def test_progress_command_prints_summary(tmp_path, capsys):
    assert cli.main(["progress", str(tmp_path)]) == 0

    assert "première session" in capsys.readouterr().out


def test_progress_command_rejects_missing_directory(tmp_path, capsys):
    assert cli.main(["progress", str(tmp_path / "absent")]) == 1
    assert "introuvable" in capsys.readouterr().err
