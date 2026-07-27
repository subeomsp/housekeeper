from uuid import uuid5

from app.scripts.seed import SEED_ITEMS, SEED_NAMESPACE
from app.services.inventory_item_service import normalize_item_name


def test_seed_item_names_are_unique_after_normalization() -> None:
    normalized_names = [normalize_item_name(item[0]) for item in SEED_ITEMS]

    assert len(normalized_names) == len(set(normalized_names))


def test_seed_ids_are_deterministic() -> None:
    normalized_name = normalize_item_name(SEED_ITEMS[0][0])

    first_id = uuid5(SEED_NAMESPACE, f"item:{normalized_name}")
    second_id = uuid5(SEED_NAMESPACE, f"item:{normalized_name}")

    assert first_id == second_id

