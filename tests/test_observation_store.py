from __future__ import annotations

import pytest

from models.observation import Observation
from storage.observation_store import ObservationStore


def _make(**overrides):
    defaults = dict(category="Authentication", claim="uses JWT", evidence=("app/auth.py",), source="Investigator")
    defaults.update(overrides)
    return Observation(**defaults)


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("category", ""),
        ("claim", "   "),
        ("evidence", ()),
        ("source", ""),
    ],
)
def test_observation_rejects_malformed_fields(field_name, value):
    with pytest.raises(ValueError):
        _make(**{field_name: value})


def test_observation_is_immutable():
    observation = _make()
    with pytest.raises(Exception):
        observation.claim = "changed"


def test_store_add_and_all():
    store = ObservationStore()
    store.add(_make())
    store.add(_make(category="Database", claim="uses SQLAlchemy", evidence=("app/database.py",)))

    assert len(store) == 2
    assert len(store.all()) == 2


def test_store_by_category_and_source():
    store = ObservationStore()
    store.add(_make(category="Authentication"))
    store.add(_make(category="Database", claim="uses SQLAlchemy", evidence=("app/database.py",)))

    assert len(store.by_category("Authentication")) == 1
    assert len(store.by_category("Nonexistent")) == 0
    assert len(store.by_source("Investigator")) == 2
