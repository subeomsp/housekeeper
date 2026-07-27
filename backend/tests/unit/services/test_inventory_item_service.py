import pytest

from app.services.inventory_item_service import normalize_item_name


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (" 우유 ", "우유"),
        ("코카콜라 제로", "코카콜라제로"),
        ("Tuna Can", "tunacan"),
        (" 코카-Cola_ 제로! ", "코카cola제로"),
    ],
)
def test_normalize_item_name(name: str, expected: str) -> None:
    assert normalize_item_name(name) == expected

