import asyncio

import pytest

from maieutik import agent
from maieutik import progress as prog
from maieutik.prompts import SDK_TOOLS_FILE, build_system_prompt, load_prompt_text


def call(tools, name, args):
    handler = next(t for t in tools if t.name == name).handler
    return asyncio.run(handler(args))


def text_of(result):
    return result["content"][0]["text"]


def learn_state():
    state = agent.SessionState()
    state.set_mode("apprendre")
    return state


# --- confinement : aucun outil natif -------------------------------------------


def test_no_native_tool_is_available_only_confined_ones(tmp_path):
    options = agent.build_options(tmp_path)

    assert options.tools == []
    for name in agent.FORBIDDEN_BUILTINS:
        assert name in options.disallowed_tools
        assert name not in options.allowed_tools
    assert all(name.startswith("mcp__maieutik__") for name in options.allowed_tools)


def test_every_custom_tool_is_allowed_and_exists(tmp_path):
    options = agent.build_options(tmp_path)
    names = {t.name for t in agent.build_tools(tmp_path)}

    assert names == set(agent.CUSTOM_TOOLS)
    for name in agent.CUSTOM_TOOLS:
        assert f"mcp__maieutik__{name}" in options.allowed_tools


def test_the_agent_runs_in_the_projects_directory(tmp_path):
    assert agent.build_options(tmp_path).cwd == str(tmp_path.resolve())


# --- deux modes ---------------------------------------------------------------


def test_default_mode_is_coding_together():
    assert agent.SessionState().mode == "ensemble" == agent.DEFAULT_MODE


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        agent.SessionState().set_mode("turbo")


def test_in_default_mode_the_agent_creates_and_edits_files(tmp_path):
    tools = agent.build_tools(tmp_path)

    created = call(tools, "write_file", {"path": "app.py", "content": "x = 1"})
    edited = call(tools, "edit_file", {"path": "app.py", "old": "x = 1", "new": "x = 2"})

    assert "Créé : app.py" in text_of(created)
    assert "+1 −1" in text_of(edited)
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "x = 2\n"


def test_in_learn_mode_the_write_tools_refuse_to_act(tmp_path):
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    tools = agent.build_tools(tmp_path, learn_state())

    attempts = [
        call(tools, "write_file", {"path": "new.py", "content": "y = 1"}),
        call(tools, "write_file", {"path": "app.py", "content": "y = 1", "overwrite": True}),
        call(tools, "edit_file", {"path": "app.py", "old": "x = 1", "new": "x = 2"}),
    ]

    for result in attempts:
        assert result["is_error"] is True
        assert "Mode apprendre" in text_of(result)
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "x = 1\n"
    assert not (tmp_path / "new.py").exists()


def test_switching_mode_takes_effect_on_the_running_tools(tmp_path):
    state = agent.SessionState()
    tools = agent.build_tools(tmp_path, state)

    state.set_mode("apprendre")
    refused = call(tools, "write_file", {"path": "a.py", "content": "1"})
    state.set_mode("ensemble")
    allowed = call(tools, "write_file", {"path": "a.py", "content": "1"})

    assert refused["is_error"] is True
    assert "is_error" not in allowed
    assert (tmp_path / "a.py").exists()


def test_reading_and_challenges_still_work_in_learn_mode(tmp_path):
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    tools = agent.build_tools(tmp_path, learn_state())

    read = call(tools, "read_file", {"path": "app.py"})
    challenge = call(
        tools, "write_challenge", {"filename": "test_x.py", "content": "def test_x():\n    assert True\n"}
    )

    assert "x = 1" in text_of(read)
    assert "is_error" not in challenge
    assert (tmp_path / "tests" / "test_x.py").exists()


# --- les outils refusent ce qui est dangereux ----------------------------------


def test_secret_files_are_neither_read_nor_written(tmp_path):
    (tmp_path / ".env").write_text("API_KEY=sk-secret\n", encoding="utf-8")
    tools = agent.build_tools(tmp_path)

    read = call(tools, "read_file", {"path": ".env"})
    write = call(tools, "write_file", {"path": ".env", "content": "API_KEY=x", "overwrite": True})
    edit = call(tools, "edit_file", {"path": ".env", "old": "sk-secret", "new": "x"})
    template = call(tools, "write_file", {"path": ".env.example", "content": "API_KEY="})

    for result in (read, write, edit):
        assert result["is_error"] is True
        assert ".env.example" in text_of(result)
    assert "sk-secret" not in text_of(read)
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "API_KEY=sk-secret\n"
    assert "is_error" not in template


def test_paths_outside_the_project_are_refused_by_every_file_tool(tmp_path):
    tools = agent.build_tools(tmp_path)
    attempts = [
        call(tools, "read_file", {"path": "../x.py"}),
        call(tools, "list_files", {"path": ".."}),
        call(tools, "search_text", {"pattern": "a", "path": "/etc"}),
        call(tools, "write_file", {"path": "../x.py", "content": "1"}),
        call(tools, "edit_file", {"path": "../x.py", "old": "a", "new": "b"}),
        call(tools, "run_python", {"file": "../evil.py"}),
    ]

    for result in attempts:
        assert result["is_error"] is True
        assert "refusé" in text_of(result)


def test_tool_errors_are_returned_not_raised(tmp_path):
    tools = agent.build_tools(tmp_path)

    result = call(tools, "read_file", {"path": "absent.py", "start": "pas un nombre"})

    assert result["is_error"] is True
    assert "invalide" in text_of(result)


# --- progression et journal ----------------------------------------------------


def test_record_progress_tool_writes_the_progress_file(tmp_path):
    tools = agent.build_tools(tmp_path)

    result = call(tools, "record_progress", {"concept": "boucles", "outcome": "solved", "help_level": 1})

    assert "boucles" in text_of(result)
    assert prog.load(tmp_path)["concepts"]["boucles"]["history"][0]["help_level"] == 1


def test_explained_concepts_are_recorded_as_seen(tmp_path):
    tools = agent.build_tools(tmp_path)

    result = call(tools, "record_progress", {"concept": "authentification", "outcome": "seen"})

    assert "vu" in text_of(result)


def test_invalid_input_is_reported_as_a_tool_error(tmp_path):
    tools = agent.build_tools(tmp_path)

    result = call(tools, "record_progress", {"concept": "x", "outcome": "peut-être"})

    assert result["is_error"] is True
    assert "invalide" in text_of(result)


def test_get_progress_tool_reflects_updates(tmp_path):
    tools = agent.build_tools(tmp_path)
    call(tools, "update_profile", {"level": "non-codeur", "milestone": 2})
    call(tools, "record_error", {"description": "oublie de vérifier qui est connecté"})

    summary = text_of(call(tools, "get_progress", {}))

    assert "non-codeur" in summary
    assert "Jalon en cours : 2" in summary
    assert "oublie de vérifier qui est connecté" in summary


def test_log_change_tool_appends_to_the_journal(tmp_path):
    tools = agent.build_tools(tmp_path)

    call(
        tools,
        "log_change",
        {
            "request": "Ajout de la connexion",
            "files": ["auth.py", "routes.py"],
            "why": "mots de passe hachés",
            "risks": "clé de session à mettre dans .env",
        },
    )
    journal = prog.journal_path(tmp_path).read_text(encoding="utf-8")

    assert "Ajout de la connexion" in journal
    assert "`auth.py`, `routes.py`" in journal
    assert "clé de session à mettre dans .env" in journal


def test_write_challenge_tool_creates_a_failing_test(tmp_path):
    tools = agent.build_tools(tmp_path)

    call(
        tools,
        "write_challenge",
        {"filename": "test_double.py", "content": "from calc import double\n\ndef test_it():\n    assert double(2) == 4\n"},
    )
    result = text_of(call(tools, "run_tests", {}))

    # Le module `calc` n'existe pas encore : le défi ne peut pas être vert,
    # et la sortie doit dire à l'élève quel module manque.
    assert "code de sortie : 0" not in result
    assert "calc" in result


# --- prompt --------------------------------------------------------------------


def test_system_prompt_contains_the_method_the_security_rules_and_the_state(tmp_path):
    data = prog.empty_progress()
    prog.record_concept(data, "dictionnaires", "stuck", 3)
    prog.save(tmp_path, data)

    prompt = build_system_prompt(tmp_path)

    assert "Échelle d'aide" in prompt
    assert "# Sécurité" in prompt
    assert "Mode actuel : coder ensemble" in prompt
    assert "dictionnaires : fragile" in prompt


def test_system_prompt_announces_the_current_mode(tmp_path):
    assert "Mode actuel : apprendre" in build_system_prompt(tmp_path, mode="apprendre")
    assert "Mode actuel : apprendre" in agent.build_options(tmp_path, state=learn_state()).system_prompt


def test_the_terminal_prompt_documents_every_tool():
    tools_doc = SDK_TOOLS_FILE.read_text(encoding="utf-8")

    for name in agent.CUSTOM_TOOLS:
        assert f"`{name}`" in tools_doc, f"{name} manque dans sdk_tools.md"
    assert load_prompt_text().count("# Tes outils dans cette session") == 1
