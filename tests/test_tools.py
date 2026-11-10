import pytest

from maieutik import tools as tl


def test_paths_cannot_escape_the_workspace(tmp_path):
    for bad in ("../secret.py", "/etc/passwd", "a/../../x"):
        with pytest.raises(tl.ToolError):
            tl.resolve_in_workspace(tmp_path, bad)


def test_paths_inside_the_workspace_are_accepted(tmp_path):
    assert tl.resolve_in_workspace(tmp_path, "src/a.py") == tmp_path.resolve() / "src" / "a.py"
    assert tl.resolve_in_workspace(tmp_path, ".") == tmp_path.resolve()


def test_symlink_escaping_the_workspace_is_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "link").symlink_to(outside)

    with pytest.raises(tl.ToolError):
        tl.resolve_in_workspace(workspace, "link/x.py")


def test_truncate_keeps_head_and_tail():
    text = "A" * 100 + "B" * 100

    short = tl.truncate(text, limit=20)

    assert short.startswith("A" * 10)
    assert short.endswith("B" * 10)
    assert "tronquée" in short


def test_run_python_returns_output_and_exit_code(tmp_path):
    (tmp_path / "hello.py").write_text("print('salut')\n", encoding="utf-8")

    assert tl.run_python(tmp_path, "hello.py") == "code de sortie : 0\nsalut"


def test_run_python_reports_tracebacks(tmp_path):
    (tmp_path / "boom.py").write_text("1 / 0\n", encoding="utf-8")

    result = tl.run_python(tmp_path, "boom.py")

    assert "code de sortie : 1" in result
    assert "ZeroDivisionError" in result


def test_run_python_stops_infinite_loops(tmp_path):
    (tmp_path / "loop.py").write_text("while True:\n    pass\n", encoding="utf-8")

    assert "Temps dépassé" in tl.run_python(tmp_path, "loop.py", timeout=1)


def test_run_python_does_not_wait_for_input(tmp_path):
    (tmp_path / "ask.py").write_text("input('? ')\n", encoding="utf-8")

    assert "EOFError" in tl.run_python(tmp_path, "ask.py", timeout=10)


def test_run_python_refuses_other_files(tmp_path):
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")

    with pytest.raises(tl.ToolError):
        tl.run_python(tmp_path, "notes.txt")
    with pytest.raises(tl.ToolError):
        tl.run_python(tmp_path, "missing.py")


def test_run_tests_reports_a_failure_then_a_success(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_math.py").write_text(
        "from calc import double\n\ndef test_double():\n    assert double(2) == 4\n",
        encoding="utf-8",
    )
    (tmp_path / "calc.py").write_text("def double(x):\n    return x\n", encoding="utf-8")

    failing = tl.run_tests(tmp_path)

    assert "code de sortie : 1" in failing
    assert "1 failed" in failing

    (tmp_path / "calc.py").write_text("def double(x):\n    return x * 2\n", encoding="utf-8")

    assert "1 passed" in tl.run_tests(tmp_path)


def test_run_tests_explains_when_nothing_is_collected(tmp_path):
    assert "Aucun test collecté" in tl.run_tests(tmp_path)


def test_run_tests_rejects_unknown_path(tmp_path):
    with pytest.raises(tl.ToolError):
        tl.run_tests(tmp_path, "nope")


def test_write_challenge_creates_the_test_file(tmp_path):
    message = tl.write_challenge(tmp_path, "test_double.py", "def test_x():\n    assert True")

    assert "tests/test_double.py" in message
    assert (tmp_path / "tests" / "test_double.py").read_text(encoding="utf-8").endswith("True\n")


def test_write_challenge_never_overwrites(tmp_path):
    tl.write_challenge(tmp_path, "test_a.py", "def test_x(): pass")

    with pytest.raises(tl.ToolError):
        tl.write_challenge(tmp_path, "test_a.py", "def test_y(): pass")
    assert "test_x" in (tmp_path / "tests" / "test_a.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["../test_a.py", "a.py", "test_A.py", "tests/test_a.py", "test_a.txt", ""])
def test_write_challenge_rejects_bad_names(tmp_path, name):
    with pytest.raises(tl.ToolError):
        tl.write_challenge(tmp_path, name, "def test_x(): pass")


def test_write_challenge_rejects_empty_content(tmp_path):
    with pytest.raises(tl.ToolError):
        tl.write_challenge(tmp_path, "test_a.py", "  \n")
