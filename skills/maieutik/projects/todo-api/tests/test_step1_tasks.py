"""Jalon 1 : ces tests échouent tant que `todo.py` n'existe pas. Fais-les passer."""

import pytest

from todo import add_task, complete_task, list_tasks


def test_add_task_returns_the_new_task():
    tasks = []

    task = add_task(tasks, "Apprendre pytest")

    assert task["title"] == "Apprendre pytest"
    assert task["done"] is False
    assert task["id"] == 1
    assert tasks == [task]


def test_ids_are_unique_and_increasing():
    tasks = []

    first = add_task(tasks, "a")
    second = add_task(tasks, "b")

    assert (first["id"], second["id"]) == (1, 2)


def test_complete_task_marks_it_done():
    tasks = []
    task = add_task(tasks, "x")

    complete_task(tasks, task["id"])

    assert tasks[0]["done"] is True


def test_complete_unknown_task_raises_key_error():
    with pytest.raises(KeyError):
        complete_task([], 42)


def test_list_tasks_can_keep_only_open_ones():
    tasks = []
    done = add_task(tasks, "a")
    still_open = add_task(tasks, "b")
    complete_task(tasks, done["id"])

    assert list_tasks(tasks, only_open=True) == [still_open]
    assert list_tasks(tasks) == [done, still_open]
