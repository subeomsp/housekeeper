from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models import Base

EXPECTED_TABLES = {
    "audit_logs",
    "households",
    "users",
    "household_members",
    "inventory_items",
    "inventory",
    "inventory_events",
    "voice_requests",
    "action_plans",
    "item_aliases",
}


def test_phase_one_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_inventory_constraints_match_specification() -> None:
    inventory = Base.metadata.tables["inventory"]
    constraint_names = {
        constraint.name
        for constraint in inventory.constraints
        if isinstance(constraint, (CheckConstraint, UniqueConstraint))
    }

    assert "uq_inventory_item" in constraint_names
    assert "ck_inventory_quantity_nonnegative" in constraint_names


def test_inventory_event_constraint_matches_specification() -> None:
    inventory_events = Base.metadata.tables["inventory_events"]
    constraint_names = {
        constraint.name
        for constraint in inventory_events.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_names == {"ck_event_quantity_positive"}


def test_action_plan_and_alias_uniqueness_match_specification() -> None:
    action_plans = Base.metadata.tables["action_plans"]
    action_plan_constraints = {
        constraint.name
        for constraint in action_plans.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_action_plan_voice_request" in action_plan_constraints

    item_aliases = Base.metadata.tables["item_aliases"]
    alias_constraints = {
        constraint.name
        for constraint in item_aliases.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_item_alias_household_normalized" in alias_constraints


def test_latest_migration_is_alembic_head() -> None:
    config = Config("alembic.ini")
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_current_head() == "20260728_0003"
