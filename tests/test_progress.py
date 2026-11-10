import json

import pytest

from maieutik import progress as prog


def solved(level):
    return {"outcome": "solved", "help_level": level}


def stuck(level=3):
    return {"outcome": "stuck", "help_level": level}


def test_status_of_an_empty_history_is_new():
    assert prog.concept_status([]) == "new"


def test_two_solved_with_at_most_a_hint_is_mastered():
    assert prog.concept_status([solved(0), solved(1)]) == "mastered"


def test_a_single_success_is_only_learning():
    assert prog.concept_status([solved(0)]) == "learning"


def test_success_needing_the_full_solution_is_shaky():
    assert prog.concept_status([solved(0), solved(3)]) == "shaky"


def test_last_attempt_stuck_is_shaky_even_after_successes():
    assert prog.concept_status([solved(0), solved(0), stuck(2)]) == "shaky"


def test_partial_example_does_not_count_towards_mastery():
    assert prog.concept_status([solved(0), solved(2)]) == "learning"


def test_load_without_file_gives_empty_progress(tmp_path):
    assert prog.load(tmp_path) == prog.empty_progress()


def test_save_then_load_roundtrip(tmp_path):
    data = prog.empty_progress()
    prog.record_concept(data, "boucles for", "solved", 1, note="à l'aise")
    prog.save(tmp_path, data)

    loaded = prog.load(tmp_path)

    assert loaded["concepts"]["boucles for"]["note"] == "à l'aise"
    assert loaded["updated_at"] is not None


def test_corrupt_file_is_backed_up_not_overwritten(tmp_path):
    path = prog.progress_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{ pas du json", encoding="utf-8")

    data = prog.load(tmp_path)

    assert data == prog.empty_progress()
    assert path.with_name(path.name + ".bak").read_text(encoding="utf-8") == "{ pas du json"


def test_non_dict_json_is_backed_up(tmp_path):
    path = prog.progress_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([1, 2]), encoding="utf-8")

    assert prog.load(tmp_path) == prog.empty_progress()
    assert path.with_name(path.name + ".bak").exists()


def test_concept_names_are_matched_case_insensitively():
    data = prog.empty_progress()
    prog.record_concept(data, "Exceptions", "solved", 0)
    prog.record_concept(data, "exceptions", "solved", 0)

    assert list(data["concepts"]) == ["Exceptions"]
    assert data["concepts"]["Exceptions"]["status"] == "mastered"


def test_history_is_capped():
    data = prog.empty_progress()
    for _ in range(prog.MAX_HISTORY + 4):
        prog.record_concept(data, "x", "solved", 0)

    assert len(data["concepts"]["x"]["history"]) == prog.MAX_HISTORY


@pytest.mark.parametrize(
    ("concept", "outcome", "level"),
    [("", "solved", 0), ("  ", "solved", 0), ("x", "gagné", 0), ("x", "solved", 4), ("x", "solved", -1)],
)
def test_invalid_records_are_rejected(concept, outcome, level):
    with pytest.raises(prog.ProgressError):
        prog.record_concept(prog.empty_progress(), concept, outcome, level)


def test_recurring_errors_are_counted_not_duplicated():
    data = prog.empty_progress()

    assert prog.record_error(data, "Oublie le return") == 1
    assert prog.record_error(data, "oublie le RETURN") == 2
    assert len(data["errors"]) == 1


def test_errors_list_is_capped_and_keeps_the_most_frequent():
    data = prog.empty_progress()
    prog.record_error(data, "fréquente")
    prog.record_error(data, "fréquente")
    for index in range(prog.MAX_ERRORS + 3):
        prog.record_error(data, f"rare {index}")

    assert len(data["errors"]) == prog.MAX_ERRORS
    assert any(item["text"] == "fréquente" for item in data["errors"])


def test_update_profile_validates_input():
    data = prog.empty_progress()
    prog.update_profile(data, level="débutant", milestone=2, project="todo-api")

    assert (data["level"], data["milestone"], data["project"]) == ("débutant", 2, "todo-api")
    with pytest.raises(prog.ProgressError):
        prog.update_profile(data, milestone=0)
    with pytest.raises(prog.ProgressError):
        prog.update_profile(data, level="  ")


def test_summary_mentions_status_and_errors():
    data = prog.empty_progress()
    prog.record_concept(data, "exceptions", "solved", 3)
    prog.record_error(data, "oublie le return")

    text = prog.summary(data)

    assert "exceptions : fragile (dernière aide : barreau 3)" in text
    assert "oublie le return (x1)" in text


def test_summary_of_a_first_session():
    assert "première session" in prog.summary(prog.empty_progress())


# --- concepts « vus » (expliqués, pas encore testés) -----------------------------


def seen():
    return {"outcome": "seen", "help_level": 0}


def test_an_explained_concept_is_seen_not_learning():
    assert prog.concept_status([seen()]) == "seen"


def test_explaining_again_never_changes_a_status_set_by_attempts():
    assert prog.concept_status([solved(0), solved(1), seen()]) == "mastered"
    assert prog.concept_status([stuck(), seen()]) == "shaky"
    assert prog.concept_status([seen(), solved(0)]) == "learning"


def test_recording_seen_twice_in_a_row_adds_one_history_entry():
    data = prog.empty_progress()

    prog.record_concept(data, "authentification", "seen")
    status = prog.record_concept(data, "authentification", "seen", note="expliqué avec une analogie")

    entry = data["concepts"]["authentification"]
    assert status == "seen"
    assert len(entry["history"]) == 1
    assert entry["note"] == "expliqué avec une analogie"


def test_seen_does_not_push_a_stuck_attempt_out_of_the_history():
    data = prog.empty_progress()
    prog.record_concept(data, "sessions", "stuck", 3)
    for _ in range(prog.MAX_HISTORY + 3):
        prog.record_concept(data, "sessions", "seen")
        prog.record_concept(data, "sessions", "solved", 0)
        prog.record_concept(data, "sessions", "stuck", 3)

    assert data["concepts"]["sessions"]["status"] == "shaky"


def test_summary_of_a_seen_concept_has_no_help_level():
    data = prog.empty_progress()
    prog.record_concept(data, "sessions", "seen")

    line = [item for item in prog.summary(data).splitlines() if "sessions" in item][0]

    assert line == "- sessions : vu"


# --- journal des changements ------------------------------------------------------


def test_journal_is_created_with_a_title_and_one_entry(tmp_path):
    path = prog.add_journal_entry(
        tmp_path, "Ajout de la connexion", ["auth.py", "routes.py"], "mots de passe hachés", "clé dans .env"
    )

    text = path.read_text(encoding="utf-8")
    assert path == prog.journal_path(tmp_path)
    assert text.startswith("# Journal des changements\n")
    assert "Ajout de la connexion" in text
    assert "- **Fichiers** : `auth.py`, `routes.py`" in text
    assert "- **Pourquoi** : mots de passe hachés" in text
    assert "- **À vérifier** : clé dans .env" in text


def test_journal_entries_are_appended_never_overwritten(tmp_path):
    prog.add_journal_entry(tmp_path, "Première demande")
    prog.add_journal_entry(tmp_path, "Deuxième demande", risks="rien")

    text = prog.journal_path(tmp_path).read_text(encoding="utf-8")

    assert text.count("# Journal des changements") == 1
    assert text.index("Première demande") < text.index("Deuxième demande")
    assert "rien de particulier signalé" in text


def test_journal_flattens_multiline_fields_to_keep_its_structure(tmp_path):
    prog.add_journal_entry(tmp_path, "Demande\n## faux titre", ["a.py\n- piège"], "ligne 1\nligne 2", "r1\n\nr2")

    text = prog.journal_path(tmp_path).read_text(encoding="utf-8")

    assert text.count("\n## ") == 1
    assert "- **Pourquoi** : ligne 1 ligne 2" in text
    assert "- **À vérifier** : r1 r2" in text


def test_journal_requires_a_request(tmp_path):
    with pytest.raises(prog.ProgressError):
        prog.add_journal_entry(tmp_path, "  \n ")
    assert not prog.journal_path(tmp_path).exists()
