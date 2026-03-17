import sqlite3
import tempfile
from pathlib import Path

from core.memory import Memory


def test_memory_init():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    memory = Memory(db_path)

    # Verify tables exist
    with sqlite3.connect(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t[0] for t in tables}

    assert "facts" in table_names
    assert "conversation_summaries" in table_names
    assert "email_cache" in table_names
    assert "action_log" in table_names

    Path(db_path).unlink()


def test_save_and_get_fact():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    memory = Memory(db_path)
    memory.save_fact("person", "Léa", "co-founder de Martin")

    facts = memory.get_facts("person")
    assert len(facts) == 1
    assert facts[0]["key"] == "Léa"
    assert facts[0]["value"] == "co-founder de Martin"

    Path(db_path).unlink()


def test_update_fact():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    memory = Memory(db_path)
    memory.save_fact("person", "Léa", "co-founder")
    memory.save_fact("person", "Léa", "co-founder et amie")

    facts = memory.get_facts("person")
    assert len(facts) == 1
    assert facts[0]["value"] == "co-founder et amie"

    Path(db_path).unlink()


def test_delete_fact():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    memory = Memory(db_path)
    memory.save_fact("preference", "lang", "français")
    assert memory.delete_fact("lang") is True
    assert memory.get_facts("preference") == []

    Path(db_path).unlink()


def test_relevant_facts_string():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    memory = Memory(db_path)
    memory.save_fact("preference", "langue", "français")
    memory.save_fact("project", "ONDES", "Bot assistant personnel")

    result = memory.get_relevant_facts()
    assert "langue" in result
    assert "ONDES" in result

    Path(db_path).unlink()


def test_action_log():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    memory = Memory(db_path)
    memory.log_action("gmail_get_emails", "filter=unread", "3 emails")

    actions = memory.get_recent_actions()
    assert len(actions) == 1
    assert actions[0]["action_type"] == "gmail_get_emails"

    Path(db_path).unlink()
