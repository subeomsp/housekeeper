from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

Quantity = Annotated[
    Decimal,
    PlainSerializer(
        lambda value: float(value),
        return_type=float,
        when_used="json",
    ),
]

