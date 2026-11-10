"""Le skill : format, autonomie, manifestes, installateurs et archive."""

import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from maieutik import __version__
from maieutik import agent
from maieutik.skill import skill_dir

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "maieutik"
SCRIPT = SKILL / "scripts" / "progress.py"


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "frontmatter manquant"
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(": ")
        fields[key] = value
    return fields


def run_script(script, *args, cwd=None):
    return subprocess.run(
        [sys.executable, "-I", str(script), *args],
        capture_output=True,
        encoding="utf-8",
        cwd=cwd,
    )


# --- format du skill ---------------------------------------------------------


def test_frontmatter_has_matching_name_and_a_bounded_description():
    fields = frontmatter(SKILL / "SKILL.md")

    assert fields["name"] == "maieutik" == SKILL.name
    assert 0 < len(fields["description"]) < 1024


def test_every_path_mentioned_in_skill_md_exists():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    paths = re.findall(r"`((?:references|scripts|projects)/[^`\s]*)`", text)

    assert paths
    for relative in paths:
        assert (SKILL / relative.rstrip("/")).exists(), relative


def test_the_method_does_not_depend_on_the_terminal_agents_tools():
    method = (SKILL / "references" / "pedagogie.md").read_text(encoding="utf-8")

    for name in agent.CUSTOM_TOOLS:
        assert name not in method, f"{name} n'a rien à faire dans la méthode partagée"


def test_the_package_reads_the_skill_from_the_source_tree():
    assert skill_dir() == SKILL


# --- script de suivi autonome ------------------------------------------------


def test_the_skills_progress_script_is_a_copy_of_the_package_module():
    source = ROOT / "src" / "maieutik" / "progress.py"

    assert SCRIPT.read_bytes() == source.read_bytes(), "lance : python3 scripts/sync_skill.py"


def test_progress_script_full_session(tmp_path):
    assert "première session" in run_script(SCRIPT, "--dir", str(tmp_path), "show").stdout

    recorded = run_script(
        SCRIPT, "--dir", str(tmp_path), "record", "boucles for", "solved", "--barreau", "1", "--note", "ok"
    )
    assert recorded.returncode == 0
    assert "boucles for" in recorded.stdout

    assert run_script(SCRIPT, "--dir", str(tmp_path), "error", "oublie le return").returncode == 0
    assert (
        run_script(
            SCRIPT, "--dir", str(tmp_path), "profile", "--level", "débutant", "--milestone", "2"
        ).returncode
        == 0
    )

    shown = run_script(SCRIPT, "--dir", str(tmp_path), "show").stdout
    assert "boucles for : en cours" in shown
    assert "oublie le return (x1)" in shown
    assert "Niveau estimé : débutant" in shown
    assert "Jalon en cours : 2" in shown


def test_progress_script_reports_errors_with_exit_code_1(tmp_path):
    args = ["--dir", str(tmp_path)]

    bad_rung = run_script(SCRIPT, *args, "record", "x", "solved", "--barreau", "4")
    empty_profile = run_script(SCRIPT, *args, "profile")
    missing_dir = run_script(SCRIPT, "--dir", str(tmp_path / "absent"), "show")

    for result in (bad_rung, empty_profile, missing_dir):
        assert result.returncode == 1
        assert result.stderr.startswith("Erreur")
    assert not (tmp_path / ".maieutik").exists(), "rien ne doit être écrit après une erreur"


def test_progress_script_rejects_an_unknown_outcome(tmp_path):
    result = run_script(SCRIPT, "--dir", str(tmp_path), "record", "x", "peut-être")

    assert result.returncode == 2


# --- manifestes du plugin ----------------------------------------------------


def test_plugin_manifests_are_consistent_with_the_package():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    pyproject_version = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)

    entry = market["plugins"][0]
    assert plugin["name"] == entry["name"] == "maieutik"
    assert plugin["version"] == entry["version"] == pyproject_version == __version__
    assert entry["source"] == "./"
    assert (ROOT / "skills").is_dir(), "le plugin découvre ses skills dans skills/"


# --- installateurs -----------------------------------------------------------


@pytest.fixture
def fake_repo(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "skills", repo / "skills")
    shutil.copytree(ROOT / "scripts", repo / "scripts")
    cache = repo / "skills" / "maieutik" / "scripts" / "__pycache__"
    cache.mkdir()
    (cache / "progress.cpython-313.pyc").write_bytes(b"x")
    return repo


def install(repo, *args, home, cwd):
    return subprocess.run(
        ["bash", str(repo / "scripts" / "install.sh"), *args],
        capture_output=True,
        encoding="utf-8",
        cwd=cwd,
        env={"PATH": "/usr/bin:/bin", "HOME": str(home)},
    )


needs_bash = pytest.mark.skipif(shutil.which("bash") is None, reason="bash indisponible")


@needs_bash
def test_install_all_puts_the_skill_in_claude_and_codex_folders(fake_repo, tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    result = install(fake_repo, "all", home=home, cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    for folder in (".claude/skills/maieutik", ".agents/skills/maieutik"):
        installed = home / folder
        assert (installed / "SKILL.md").is_file()
        assert (installed / "references" / "pedagogie.md").is_file()
        assert (installed / "projects" / "todo-api" / "PROJECT.md").is_file()
        assert not list(installed.rglob("__pycache__"))


@needs_bash
def test_install_target_and_project_flag(fake_repo, tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "proj"
    home.mkdir()
    project.mkdir()

    result = install(fake_repo, "codex", "--project", home=home, cwd=project)

    assert result.returncode == 0, result.stderr
    assert (project / ".agents" / "skills" / "maieutik" / "SKILL.md").is_file()
    assert not (project / ".claude").exists()
    assert not (home / ".agents").exists()


@needs_bash
def test_install_replaces_a_previous_install_cleanly(fake_repo, tmp_path):
    home = tmp_path / "home"
    stale = home / ".claude" / "skills" / "maieutik" / "vieux.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("obsolète", encoding="utf-8")

    install(fake_repo, "claude", home=home, cwd=tmp_path)

    assert not stale.exists()
    assert (stale.parent / "SKILL.md").is_file()


@needs_bash
def test_install_rejects_unknown_arguments(fake_repo, tmp_path):
    result = install(fake_repo, "vim", home=tmp_path, cwd=tmp_path)

    assert result.returncode == 1
    assert "inconnu" in result.stderr


@needs_bash
def test_an_installed_skill_works_without_the_python_package(fake_repo, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    install(fake_repo, "claude", home=home, cwd=tmp_path)
    installed_script = home / ".claude" / "skills" / "maieutik" / "scripts" / "progress.py"
    student = tmp_path / "eleve"
    student.mkdir()

    result = run_script(installed_script, "--dir", str(student), "record", "fonctions", "solved")

    assert result.returncode == 0, result.stderr
    assert (student / ".maieutik" / "progress.json").is_file()


# --- archive pour claude.ai --------------------------------------------------


def test_zip_contains_the_skill_folder_at_its_root(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_zips.py"), "--out", str(tmp_path)],
        capture_output=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr

    with zipfile.ZipFile(tmp_path / "maieutik-skill.zip") as archive:
        names = archive.namelist()

    assert "maieutik/SKILL.md" in names
    assert "maieutik/references/pedagogie.md" in names
    assert "maieutik/scripts/progress.py" in names
    assert "maieutik/projects/todo-api/PROJECT.md" in names
    assert all(name.startswith("maieutik/") for name in names)
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
