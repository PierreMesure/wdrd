"""Optional verification using unmodified upstream QS3, without HTTP or DB."""
import copy
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
from wdrd.quickstatements import serialize_item

@pytest.fixture(scope="module")
def parser():
    source = os.environ.get("QS3_SOURCE")
    if not source:
        pytest.skip("Set QS3_SOURCE to run upstream parser verification")
    sys.path.insert(0, str(Path(source).resolve() / "src"))
    from django.conf import settings
    if not settings.configured:
        settings.configure(INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes", "core"],
            SECRET_KEY="offline", OAUTH_CLIENT_ID="", OAUTH_CLIENT_SECRET="", OAUTH_ACCESS_TOKEN_URL="",
            OAUTH_AUTHORIZATION_URL="", DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})
    import django
    django.setup()
    from core.parsers.v1 import V1CommandParser
    return V1CommandParser()

def expected_value(snak):
    kind = snak["snaktype"]
    if kind != "value":
        return {"type": kind, "value": kind}
    dv = copy.deepcopy(snak["datavalue"])
    if dv["type"] == "wikibase-entityid":
        v = dv["value"]
        dv["value"] = v.get("id") or f'Q{v["numeric-id"]}'
    elif dv["type"] == "time":
        for key in ("timezone", "before", "after"):
            assert dv["value"].pop(key, 0) == 0
    return dv

def pairs(mapping):
    return [{"property": p, "value": expected_value(s)} for p, snaks in mapping.items() for s in snaks]

def roundtrip(parser, data):
    commands = list(parser.parse(serialize_item(data)))
    assert commands[0].json == {"action": "create", "type": "item"}
    for c in commands:
        assert c.status != c.STATUS_ERROR, c.message
    expected = []
    for field, what in [("labels", "label"), ("descriptions", "description"), ("aliases", "alias")]:
        for lang, terms in data.get(field, {}).items():
            for term in terms if field == "aliases" else [terms]:
                val = {"type": "aliases", "value": [term["value"]]} if field == "aliases" else {"type": "string", "value": term["value"]}
                expected.append({"action": "add", "what": what, "item": "LAST", "language": lang, "value": val})
    for prop, statements in data["claims"].items():
        for st in statements:
            c = {"action": "add", "what": "statement", "entity": {"type": "item", "id": "LAST"}, "property": prop, "value": expected_value(st["mainsnak"])}
            if st.get("rank", "normal") != "normal":
                c["rank"] = st["rank"]
            if st.get("qualifiers"):
                c["qualifiers"] = pairs(st["qualifiers"])
            if st.get("references"):
                c["references"] = [pairs(r["snaks"]) for r in st["references"]]
            expected.append(c)
    assert [c.json for c in commands[1:]] == expected
    return commands

def test_every_transformed_datum_roundtrips(parser, data):
    roundtrip(parser, data)

def test_extended_data_roundtrips(parser, data):
    data["aliases"] = {"sv": [{"language": "sv", "value": "Åäö | || /* text */"}]}
    st = data["claims"]["P50"][0]
    st["rank"] = "preferred"
    ref = copy.deepcopy(st["references"][0])
    ref["snaks"]["P8433"][0]["datavalue"]["value"] = "DEMO0002"
    st["references"].append(ref)
    data["claims"]["P50"][1]["rank"] = "deprecated"
    roundtrip(parser, data)

@pytest.mark.parametrize("kind", ["somevalue", "novalue"])
def test_special_value_create_payload_offline(parser, data, kind):
    snak = data["claims"]["P50"][0]["mainsnak"]
    snak.pop("datavalue")
    snak["snaktype"] = kind
    data["claims"]["P50"][0]["rank"] = "preferred"
    cmds = roundtrip(parser, data)
    entity = cmds[0].get_entity_or_empty_entity(None)
    for cmd in cmds[1:]:
        cmd._state.fields_cache["batch"] = SimpleNamespace(wikibase=SimpleNamespace(url="https://www.wikidata.org"))
        cmd.update_entity_json(entity)
    assert entity["statements"]["P50"][0]["value"] == {"type": kind}
    assert entity["statements"]["P50"][0]["rank"] == "preferred"
    assert entity["statements"]["P50"][0]["qualifiers"][0]["value"]["content"] == "1"

@pytest.mark.parametrize("calendar", ["Q1985727", "Q1985786", "Q999999"])
@pytest.mark.parametrize("precision", [0, 8, 9, 10, 11, 14])
def test_calendars_and_precision(parser, data, calendar, precision):
    val = data["claims"]["P577"][0]["mainsnak"]["datavalue"]["value"]
    val["precision"] = precision
    val["calendarmodel"] = "http://www.wikidata.org/entity/" + calendar
    roundtrip(parser, data)

def test_multiple_create_boundaries(parser, data):
    cmds = list(parser.parse(serialize_item(data) * 2))
    n = len(cmds) // 2
    assert cmds[0].json == cmds[n].json == {"action": "create", "type": "item"}
    assert [c.json for c in cmds[:n]] == [c.json for c in cmds[n:]]

def test_parser_text_loss_is_real(parser):
    assert parser.parse_command('LAST\tLsv\t"“Hej”"')["value"]["value"] == '"Hej"'
    assert parser.parse_command('LAST\tLsv\t" text "')["value"]["value"] == 'text'
    assert parser.parse_command('LAST\tLsv\t"a\\nb"')["value"]["value"] == 'a\\nb'

def test_identical_mainsnaks_keep_separate_statements(parser, data):
    second = copy.deepcopy(data["claims"]["P50"][0])
    second["qualifiers"]["P1545"][0]["datavalue"]["value"] = "3"
    data["claims"]["P50"].append(second)
    cmds = list(parser.parse(serialize_item(data)))
    entity = cmds[0].get_entity_or_empty_entity(None)
    for cmd in cmds[1:]:
        cmd._state.fields_cache["batch"] = SimpleNamespace(wikibase=SimpleNamespace(url="https://www.wikidata.org"))
        cmd.update_entity_json(entity)
    assert len(entity["statements"]["P50"]) == 3
    assert entity["statements"]["P50"][2]["qualifiers"][0]["value"]["content"] == "3"
