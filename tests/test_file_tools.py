"""Outils de lecture et d'écriture confinés au projet."""

import os

import pytest

from maieutik import tools as tl


def make(tmp_path, name, content="", binary=False):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


# --- fichiers sensibles ---------------------------------------------------------


@pytest.mark.parametrize(
    "name", [".env", ".env.local", ".env.production", "key.pem", "server.key", "id_rsa", ".npmrc", "config/.env"]
)
def test_secret_looking_files_are_sensitive(name):
    assert tl.is_sensitive(name)


@pytest.mark.parametrize("name", [".env.example", ".env.sample", "app.py", "environment.md", "keyboard.py"])
def test_ordinary_files_are_not_sensitive(name):
    assert not tl.is_sensitive(name)


# --- read_file ------------------------------------------------------------------


def test_read_file_numbers_the_lines(tmp_path):
    make(tmp_path, "a.py", "un\ndeux\ntrois\n")

    assert tl.read_file(tmp_path, "a.py") == "    1\tun\n    2\tdeux\n    3\ttrois"


def test_read_file_pages_with_start_and_limit(tmp_path):
    make(tmp_path, "a.py", "\n".join(f"l{i}" for i in range(1, 11)))

    page = tl.read_file(tmp_path, "a.py", start=3, limit=2)

    assert "    3\tl3" in page and "    4\tl4" in page and "l5" not in page.split("[")[0]
    assert "6 lignes de plus : relis avec start=5" in page


def test_read_file_handles_empty_files_and_bad_ranges(tmp_path):
    make(tmp_path, "empty.py", "")
    make(tmp_path, "a.py", "x\n")

    assert tl.read_file(tmp_path, "empty.py") == "(fichier vide)"
    for start, limit in ((0, 10), (1, 0), (1, tl.MAX_READ_LINES + 1)):
        with pytest.raises(tl.ToolError):
            tl.read_file(tmp_path, "a.py", start, limit)
    with pytest.raises(tl.ToolError):
        tl.read_file(tmp_path, "a.py", start=5)


def test_read_file_cuts_very_long_lines(tmp_path):
    make(tmp_path, "min.js", "x" * 5000)

    assert len(tl.read_file(tmp_path, "min.js")) < 500


def test_read_file_refuses_binary_huge_missing_and_secret_files(tmp_path):
    make(tmp_path, "img.png", b"\x89PNG\x00\x00", binary=True)
    make(tmp_path, "big.txt", "a" * (tl.MAX_FILE_BYTES + 1))
    make(tmp_path, ".env", "KEY=1")
    (tmp_path / "dossier").mkdir()

    for name, fragment in (
        ("img.png", "binaire"),
        ("big.txt", "trop gros"),
        ("absent.py", "introuvable"),
        ("dossier", "introuvable"),
        (".env", "secrets"),
    ):
        with pytest.raises(tl.ToolError, match=fragment):
            tl.read_file(tmp_path, name)


def test_read_file_cannot_leave_the_project_through_a_symlink(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    make(outside, "secret.txt", "top secret")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "link").symlink_to(outside)

    with pytest.raises(tl.ToolError, match="refusé"):
        tl.read_file(workspace, "link/secret.txt")


# --- list_files -----------------------------------------------------------------


def test_list_files_skips_technical_folders_and_flags_secrets(tmp_path):
    for name in ("app.py", "sub/b.py", "node_modules/x.js", ".git/config", "__pycache__/a.pyc", ".env"):
        make(tmp_path, name, "x")

    listing = tl.list_files(tmp_path).splitlines()

    assert "app.py" in listing and "sub/b.py" in listing
    assert ".env  (non lisible : secrets)" in listing
    assert not any(name.startswith(("node_modules", ".git", "__pycache__")) for name in listing)


def test_list_files_can_target_a_subfolder_and_reports_emptiness(tmp_path):
    make(tmp_path, "sub/b.py", "x")
    make(tmp_path, "a.py", "x")
    (tmp_path / "vide").mkdir()

    assert tl.list_files(tmp_path, "sub") == "sub/b.py"
    assert tl.list_files(tmp_path, "vide") == "(aucun fichier)"
    with pytest.raises(tl.ToolError):
        tl.list_files(tmp_path, "absent")


def test_list_files_is_capped(tmp_path):
    for index in range(tl.LIST_LIMIT + 5):
        make(tmp_path, f"f{index:03}.txt", "x")

    listing = tl.list_files(tmp_path).splitlines()

    assert len(listing) == tl.LIST_LIMIT + 1
    assert "5 fichiers de plus" in listing[-1]


# --- search_text ----------------------------------------------------------------


def test_search_text_reports_file_and_line(tmp_path):
    make(tmp_path, "a.py", "x = 1\nlogin = True\n")
    make(tmp_path, "sub/b.py", "def login():\n    pass\n")

    assert tl.search_text(tmp_path, "login").splitlines() == [
        "a.py:2: login = True",
        "sub/b.py:1: def login():",
    ]


def test_search_text_ignores_secrets_binaries_and_dependencies(tmp_path):
    make(tmp_path, "a.py", "login")
    make(tmp_path, ".env", "SECRET=login")
    make(tmp_path, "data.bin", b"\x00login", binary=True)
    make(tmp_path, "node_modules/x.js", "login")

    assert tl.search_text(tmp_path, "login") == "a.py:1: login"


def test_search_text_options_and_errors(tmp_path):
    make(tmp_path, "a.py", "Login\n")

    assert tl.search_text(tmp_path, "login") == "Aucun résultat."
    assert tl.search_text(tmp_path, "login", ignore_case=True) == "a.py:1: Login"
    with pytest.raises(tl.ToolError, match="invalide"):
        tl.search_text(tmp_path, "(")
    with pytest.raises(tl.ToolError):
        tl.search_text(tmp_path, "a", path="absent")


def test_search_text_is_capped(tmp_path):
    make(tmp_path, "a.txt", "hit\n" * (tl.SEARCH_LIMIT + 7))

    result = tl.search_text(tmp_path, "hit").splitlines()

    assert len(result) == tl.SEARCH_LIMIT + 1
    assert "7 résultats de plus" in result[-1]


# --- write_file -----------------------------------------------------------------


def test_write_file_creates_parent_folders_and_a_final_newline(tmp_path):
    message = tl.write_file(tmp_path, "app/models/user.py", "class User:\n    pass")

    assert message == "Créé : app/models/user.py (2 lignes)"
    assert (tmp_path / "app" / "models" / "user.py").read_text(encoding="utf-8") == "class User:\n    pass\n"


def test_write_file_never_replaces_silently(tmp_path):
    make(tmp_path, "a.py", "ancien\n")

    with pytest.raises(tl.ToolError, match="existe déjà"):
        tl.write_file(tmp_path, "a.py", "nouveau")
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "ancien\n"


def test_write_file_overwrite_shows_what_changed(tmp_path):
    make(tmp_path, "a.py", "ancien\n")

    message = tl.write_file(tmp_path, "a.py", "nouveau", overwrite=True)

    assert message.startswith("Remplacé : a.py (+1 −1)")
    assert "-ancien" in message and "+nouveau" in message


@pytest.mark.parametrize(
    ("path", "fragment"),
    [
        ("../x.py", "refusé"),
        ("/tmp/x.py", "refusé"),
        (".env", "secrets"),
        ("config/.env.production", "secrets"),
        ("deploy.pem", "secrets"),
        (".git/hooks/pre-commit", "géré à part"),
        (".maieutik/progress.json", "géré à part"),
        ("", "vide"),
        (".", "dossier"),
    ],
)
def test_write_file_refuses_dangerous_targets(tmp_path, path, fragment):
    with pytest.raises(tl.ToolError, match=fragment):
        tl.write_file(tmp_path, path, "x")


def test_write_file_accepts_env_templates(tmp_path):
    tl.write_file(tmp_path, ".env.example", "API_KEY=")

    assert (tmp_path / ".env.example").exists()


def test_write_file_refuses_a_folder_and_oversized_content(tmp_path):
    (tmp_path / "dossier").mkdir()

    with pytest.raises(tl.ToolError, match="dossier"):
        tl.write_file(tmp_path, "dossier", "x")
    with pytest.raises(tl.ToolError, match="trop gros"):
        tl.write_file(tmp_path, "big.txt", "a" * (tl.MAX_WRITE_BYTES + 1))


def test_write_file_cannot_leave_the_project_through_a_symlink(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "link").symlink_to(outside)

    with pytest.raises(tl.ToolError, match="refusé"):
        tl.write_file(workspace, "link/x.py", "evil")
    assert not (outside / "x.py").exists()


def test_a_failed_write_leaves_no_temporary_file(tmp_path, monkeypatch):
    def boom(src, dst):
        raise OSError("disque plein")

    monkeypatch.setattr(os, "replace", boom)

    with pytest.raises(OSError):
        tl.write_file(tmp_path, "a.py", "x")
    assert list(tmp_path.iterdir()) == []


# --- edit_file ------------------------------------------------------------------


def test_edit_file_replaces_one_exact_occurrence_and_returns_the_diff(tmp_path):
    make(tmp_path, "a.py", "x = 1\ny = 2\n")

    message = tl.edit_file(tmp_path, "a.py", "x = 1", "x = 10")

    assert message.startswith("Modifié : a.py (+1 −1)")
    assert "-x = 1" in message and "+x = 10" in message
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "x = 10\ny = 2\n"


def test_edit_file_requires_a_unique_match_unless_told_otherwise(tmp_path):
    make(tmp_path, "a.py", "a\na\n")

    with pytest.raises(tl.ToolError, match="2 fois"):
        tl.edit_file(tmp_path, "a.py", "a", "b")
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "a\na\n"

    tl.edit_file(tmp_path, "a.py", "a", "b", replace_all=True)

    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "b\nb\n"


@pytest.mark.parametrize(
    ("old", "new", "fragment"),
    [("absent", "x", "introuvable"), ("", "x", "vide"), ("a", "a", "identique")],
)
def test_edit_file_rejects_useless_edits(tmp_path, old, new, fragment):
    make(tmp_path, "a.py", "a\n")

    with pytest.raises(tl.ToolError, match=fragment):
        tl.edit_file(tmp_path, "a.py", old, new)


def test_edit_file_refuses_missing_secret_and_protected_files(tmp_path):
    make(tmp_path, ".env", "K=1")
    make(tmp_path, ".git/config", "x")

    for path, fragment in (("absent.py", "introuvable"), (".env", "secrets"), (".git/config", "géré à part")):
        with pytest.raises(tl.ToolError, match=fragment):
            tl.edit_file(tmp_path, path, "x", "y")


def test_edit_file_refuses_non_utf8_files(tmp_path):
    make(tmp_path, "a.bin", b"\xff\xfe\x00", binary=True)

    with pytest.raises(tl.ToolError, match="UTF-8"):
        tl.edit_file(tmp_path, "a.bin", "x", "y")


def test_edit_file_keeps_windows_line_endings_and_file_mode(tmp_path):
    path = make(tmp_path, "run.sh", b"a\r\nb\r\n", binary=True)
    path.chmod(0o755)

    tl.edit_file(tmp_path, "run.sh", "b", "c")

    assert path.read_bytes() == b"a\r\nc\r\n"
    assert path.stat().st_mode & 0o777 == 0o755
