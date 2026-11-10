import asyncio

from maieutik import agent
from maieutik import progress as prog
from maieutik.prompts import build_system_prompt, load_prompt_text


def call(tools, name, args):
    handler = next(t for t in tools if t.name == name).handler
    return asyncio.run(handler(args))


def text_of(result):
    return result["content"][0]["text"]


def test_the_agent_cannot_modify_the_students_files(tmp_path):
    options = agent.build_options(tmp_path)

    assert set(options.tools) == {"Read", "Glob", "Grep"}
    for forbidden in ("Write", "Edit", "Bash"):
        assert forbidden in options.disallowed_tools
        assert forbidden not in options.allowed_tools


def test_every_custom_tool_is_allowed_and_exists(tmp_path):
    options = agent.build_options(tmp_path)
    names = {t.name for t in agent.build_tools(tmp_path)}

    assert names == set(agent.CUSTOM_TOOLS)
    for name in agent.CUSTOM_TOOLS:
        assert f"mcp__maieutik__{name}" in options.allowed_tools


def test_the_agent_runs_in_the_students_directory(tmp_path):
    assert agent.build_options(tmp_path).cwd == str(tmp_path.resolve())


def test_system_prompt_contains_the_rules_and_the_students_state(tmp_path):
    data = prog.empty_progress()
    prog.record_concept(data, "dictionnaires", "stuck", 3)
    prog.save(tmp_path, data)

    prompt = build_system_prompt(tmp_path)

    assert "Échelle d'aide" in prompt
    assert "jamais la solution" in prompt
    assert "dictionnaires : fragile" in prompt


def test_prompts_mention_every_custom_tool():
    text = load_prompt_text()
    for name in ("get_progress", "record_progress", "record_error", "update_profile", "write_challenge"):
        assert name in text


def test_record_progress_tool_writes_the_progress_file(tmp_path):
    tools = agent.build_tools(tmp_path)

    result = call(tools, "record_progress", {"concept": "boucles", "outcome": "solved", "help_level": 1})

    assert "boucles" in text_of(result)
    assert prog.load(tmp_path)["concepts"]["boucles"]["history"][0]["help_level"] == 1


def test_invalid_input_is_reported_as_a_tool_error(tmp_path):
    tools = agent.build_tools(tmp_path)

    result = call(tools, "record_progress", {"concept": "x", "outcome": "peut-être"})

    assert result["is_error"] is True
    assert "invalide" in text_of(result)


def test_tool_errors_are_returned_not_raised(tmp_path):
    tools = agent.build_tools(tmp_path)

    result = call(tools, "run_python", {"file": "../evil.py"})

    assert result["is_error"] is True
    assert "refusé" in text_of(result)


def test_get_progress_tool_reflects_updates(tmp_path):
    tools = agent.build_tools(tmp_path)
    call(tools, "update_profile", {"level": "débutant", "milestone": 2})
    call(tools, "record_error", {"description": "oublie le return"})

    summary = text_of(call(tools, "get_progress", {}))

    assert "débutant" in summary
    assert "Jalon en cours : 2" in summary
    assert "oublie le return" in summary


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
