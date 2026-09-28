import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from wdrd import export_docs, prepare_docs
from wdrd.quickstatements import ExportError, serialize_item


def test_wdi_fixture_and_whole_blocks(item, data, tmp_path):
    block = serialize_item(item)
    assert block == serialize_item(data)
    report = export_docs([item, item], tmp_path / "items.qs")
    assert report["exported"] == 2  # Deliberately no document deduplication.
    assert (tmp_path / "items.qs").read_text() == block * 2
    assert block.startswith("CREATE\nLAST\tLsv\t")
    for rank, qid in [(1, "Q111"), (2, "Q222")]:
        assert f'LAST\tP50\t{qid}\tP1545\t"{rank}"' in block
    assert 'LAST\tP1478\tQ456\n' in block
    assert json.loads((tmp_path / "items.qs.report.json").read_text()) == report


@pytest.mark.parametrize("text", ['citat "text"', 'a\\b', 'a\tb', 'a\nb', 'a\rb',
                                   '“text”', ' text', 'text ', '___QSTS3_PLACEHOLDER___'])
def test_unsafe_text_rejects_whole_item(data, text, tmp_path):
    bad = copy.deepcopy(data)
    bad["claims"]["P1476"][0]["mainsnak"]["datavalue"]["value"]["text"] = text
    path = tmp_path / "out.qs"
    report = export_docs([data, bad, data], path)
    assert (report["exported"], report["rejected"]) == (2, 1)
    assert path.read_text() == serialize_item(data) * 2
    assert report["errors"][0]["document_id"] == "DEMO0001"


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(sitelinks={"svwiki": {"title": "Exempel"}}),
    lambda d: d.update(unknown="must not disappear"),
    lambda d: d.update(id="Q123"),
    lambda d: d["claims"]["P50"][0].update(rank="invalid"),
    lambda d: d["claims"]["P577"][0]["mainsnak"]["datavalue"]["value"].update(before=1),
    lambda d: d["claims"]["P577"][0]["mainsnak"]["datavalue"]["value"].update(timezone=60),
    lambda d: d["claims"]["P50"][0]["mainsnak"].update(datatype="globe-coordinate"),
    lambda d: d["claims"]["P50"][0].update(qualifiers_order=["P1"]),
])
def test_unsupported_data_is_explicit(data, mutation):
    mutation(data)
    with pytest.raises(ExportError):
        serialize_item(data)


@pytest.mark.parametrize("precision", [0, 8, 9, 10, 11, 14])
def test_time_precision(data, precision):
    data["claims"]["P577"][0]["mainsnak"]["datavalue"]["value"]["precision"] = precision
    assert f'LAST\tP577\t+2024-10-01T00:00:00Z/{precision}' in serialize_item(data)


@pytest.mark.parametrize("kind", ["somevalue", "novalue"])
def test_special_values_with_last(data, kind):
    snak = data["claims"]["P50"][0]["mainsnak"]
    snak.pop("datavalue")
    snak["snaktype"] = kind
    assert f'LAST\tP50\t{kind}\tP1545' in serialize_item(data)


def test_prepare_export_skips_existing_only(monkeypatch):
    from wdrd.document import DocumentCollection
    remove = Mock(side_effect=AssertionError("Must not query existing documents"))
    monkeypatch.setattr(DocumentCollection, "_remove_existing_docs", remove)
    raw = [{"rm": "2024/25", "doktyp": "mot", "titel": "Motionen utgår", "id": "1"},
           {"rm": "2024/25", "doktyp": "mot", "titel": "Behåll", "id": "2"}]
    collection = prepare_docs(raw, remove_existing=False)
    assert [d.doc_id for d in collection.docs] == ["2"]
    assert collection.invalid_count == 1
    assert collection.filtered_documents[0]["reason"] == "Motionen utgår"
    remove.assert_not_called()
    assert prepare_docs([], remove_existing=False).docs == []
    remove = Mock(side_effect=lambda docs: docs)
    monkeypatch.setattr(DocumentCollection, "_remove_existing_docs", remove)
    prepare_docs(raw)
    remove.assert_called_once()


def test_invalid_proposition_filter():
    raw = [{"rm": "2024/25", "doktyp": "prop", "titel": "X", "subtyp": "bilaga", "id": "1"}]
    assert prepare_docs(raw, remove_existing=False).invalid_count == 1


def test_export_does_not_login_or_write(item, tmp_path, monkeypatch):
    from wikidataintegrator import wdi_core, wdi_login
    forbidden = Mock(side_effect=AssertionError("Upload path reached"))
    monkeypatch.setattr(wdi_login, "WDLogin", forbidden)
    monkeypatch.setattr(wdi_core.WDItemEngine, "write", forbidden)
    export_docs([item], tmp_path / "out.qs")
    forbidden.assert_not_called()


def test_import_is_stdlib_only_and_no_authentication(tmp_path):
    code = '''
import builtins, socket
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in ('wikidataintegrator', 'requests', 'pandas'):
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError('network'))
import wdrd
import wdrd.quickstatements
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_upload_auth_is_lazy(monkeypatch):
    from wikidataintegrator import wdi_login
    import importlib
    login = Mock(return_value=object())
    monkeypatch.setattr(wdi_login, "WDLogin", login)
    import wdrd.load
    importlib.reload(wdrd.load)
    login.assert_not_called()
    # An explicit upload with an empty collection tests login routing; no .write().
    wdrd.load.load_collection([])
    login.assert_called_once()


def test_io_failure_keeps_previous_output(data, tmp_path):
    path = tmp_path / "out.qs"
    path.write_text("previous")
    def broken():
        yield data
        raise RuntimeError("iterator failed")
    with pytest.raises(RuntimeError):
        export_docs(broken(), path)
    assert path.read_text() == "previous"


def test_report_counts_and_paths(data, tmp_path):
    report = export_docs([data, {}], tmp_path / "out.qs", filtered_documents=[{"document_id": "x", "reason": "invalid"}])
    assert (report["input"], report["exported"], report["filtered"], report["rejected"]) == (3, 1, 1, 1)
    with pytest.raises(ExportError):
        export_docs([data], tmp_path / "out.qs", report_path=tmp_path / "out.qs")


def test_cli_offline(data, tmp_path):
    source = tmp_path / "items.json"
    source.write_text(json.dumps([data, {}]))
    result = subprocess.run([sys.executable, "-m", "wdrd", "--items-json", str(source),
                             "--output", str(tmp_path / "out.qs")], capture_output=True, text=True)
    assert result.returncode == 2, result.stderr
    assert json.loads(result.stdout)["exported"] == 1

def test_real_document_collection_through_transform(monkeypatch, tmp_path):
    import pandas as pd
    from wdrd import sparql, transform_docs, wd_item
    monkeypatch.setattr(wd_item.wdi_core.WDItemEngine, "DISTINCT_VALUE_PROPS", {"https://query.wikidata.org/sparql": set()})
    monkeypatch.setattr(wd_item.wdi_core, "MappingRelationHelper", lambda *a, **k: None)
    monkeypatch.setattr(sparql, "get_series_qid", lambda *a: "Q123")
    monkeypatch.setattr(sparql, "get_people", lambda: pd.DataFrame([
        {"code": "a", "item": "Q111", "itemLabel": "Anna Åberg"},
        {"code": "b", "item": "Q222", "itemLabel": "Östen Öberg"}]))
    def propositions_only(session, doc_type):
        assert doc_type == "prop"  # A motion existence lookup must never happen.
        return pd.DataFrame([{"ref": "prop. 2024/25:1", "item": "Q456"}])
    monkeypatch.setattr(sparql, "get_series_docs", propositions_only)
    raw = {"id": "DEMO0001", "doktyp": "mot", "datum": "2024-10-01", "typ": "mot",
           "titel": "Med anledning av prop. 2024/25:1", "rm": "2024/25", "subtyp": "Följdmotion",
           "organ": "TU", "beteckning": "1", "filbilaga": None,
           "dokintressent": {"intressent": [{"roll": "undertecknare", "namn": "Anna Åberg", "intressent_id": "a"},
                                          {"roll": "undertecknare", "namn": "Östen Öberg", "intressent_id": "b"}]}}
    collection = prepare_docs([raw], remove_existing=False)
    report = export_docs(transform_docs(collection), tmp_path / "out.qs")
    assert report["exported"] == 1
    output = (tmp_path / "out.qs").read_text()
    assert 'LAST\tP1478\tQ456' in output
    assert 'LAST\tP50\tQ222\tP1545\t"2"' in output
