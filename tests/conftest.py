import copy
from datetime import datetime
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError("Network access is forbidden in the test suite")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    import requests
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)


@pytest.fixture
def document_input():
    return SimpleNamespace(
        doc_id="DEMO0001", doc_type="mot", date="+2024-10-01T00:00:00Z",
        title="Exempel: järnväg i Kalmar län", series="Q123", session="2024/25",
        ordinal="1", subtype="Q96739634", committee="Q10701059",
        html="https://example.org/document/1", xml="https://example.org/status/1",
        pdf="https://example.org/1.pdf", cause="Q456",
        authors=[{"name": "Anna Åberg", "qid": "Q111"}, {"name": "Östen Öberg", "qid": "Q222"}],
        respondent=None,
    )


@pytest.fixture
def item(document_input, monkeypatch):
    from wdrd import wd_item
    # WDI fetches unique-value property constraints even for new_item=True.
    # Stub only that unrelated network lookup, not Wdrd's transformation.
    monkeypatch.setattr(wd_item.wdi_core.WDItemEngine, "DISTINCT_VALUE_PROPS", {"https://query.wikidata.org/sparql": set()})
    monkeypatch.setattr(wd_item.wdi_core, "MappingRelationHelper", lambda *a, **k: None)
    class FixedDateTime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 22)
    monkeypatch.setattr(wd_item, "datetime", FixedDateTime)
    return wd_item.create_item(document_input)


@pytest.fixture
def data(item):
    return copy.deepcopy(item.get_wd_json_representation())
