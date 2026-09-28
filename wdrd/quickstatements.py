"""Lossless, offline export of new WDI items to QuickStatements 3 V1 syntax.

Conservative by design: unsupported input rejects the entire item. No API calls.
See docs/quickstatements.md for the audited parser and representability limits.
"""
import json
import os
import re
import tempfile
from pathlib import Path


class ExportError(ValueError):
    """An item cannot be represented without loss in the supported QS dialect."""


def _check(condition, message):
    if not condition:
        raise ExportError(message)


def _keys(value, allowed, context):
    _check(isinstance(value, dict), f"{context}: expected an object")
    extra = set(value) - set(allowed.split())
    _check(not extra, f"{context}: unsupported fields {sorted(extra)}")


def _id(value, prefix):
    _check(isinstance(value, str) and re.fullmatch(prefix + r"[1-9]\d*", value),
           f"Invalid {prefix} identifier: {value!r}")
    return value


def _language(value):
    _check(isinstance(value, str) and re.fullmatch(r"[a-z]+(?:-[a-z]+)*", value),
           f"Unsupported language code: {value!r}")
    return value


def _text(value):
    _check(isinstance(value, str), "Expected a string")
    _check(value == value.strip(), "QS3 strips leading/trailing whitespace")
    _check(not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value),
           "Control characters (including tabs/newlines) cannot be exported")
    _check(not any(c in value for c in ('"', '\\', '“', '”', '\u2028', '\u2029')),
           "Quotes, backslashes or Unicode line separators are outside the lossless text subset")
    _check('___QSTS3_PLACEHOLDER___' not in value, "Text collides with QS3 parser placeholder")
    # No JSON escaping: QS3 does not decode JSON escapes in V1 strings.
    return '"' + value + '"'


def _value(snak):
    _keys(snak, "snaktype property datatype datavalue hash", "snak")
    _id(snak["property"], "P")
    kind = snak["snaktype"]
    if kind in ("somevalue", "novalue"):
        _check("datavalue" not in snak, f"{kind} unexpectedly has datavalue")
        return kind
    _check(kind == "value", f"Unsupported snaktype: {kind!r}")
    dv = snak["datavalue"]
    _keys(dv, "type value", "datavalue")
    value, dtype = dv["value"], snak["datatype"]
    expected = {"wikibase-item": "wikibase-entityid", "string": "string",
                "external-id": "string", "url": "string",
                "monolingualtext": "monolingualtext", "time": "time"}
    _check(dtype in expected, f"Unsupported datatype: {dtype!r}")
    _check(dv["type"] == expected[dtype], f"Mismatched datavalue type for {dtype}")
    if dtype in ("string", "external-id", "url"):
        return _text(value)
    if dtype == "wikibase-item":
        _keys(value, "entity-type numeric-id id", "entity value")
        _check(value.get("entity-type", "item") == "item", "Expected item entity")
        qid = value.get("id")
        if qid is None:
            number = value["numeric-id"]
            _check(type(number) is int and number > 0, "Invalid numeric-id")
            qid = f"Q{number}"
        _id(qid, "Q")
        if "numeric-id" in value:
            _check(type(value["numeric-id"]) is int and value["numeric-id"] == int(qid[1:]),
                   "Conflicting entity id and numeric-id")
        return qid
    if dtype == "monolingualtext":
        _keys(value, "text language", "monolingual value")
        return _language(value["language"]) + ":" + _text(value["text"])
    _keys(value, "time precision timezone before after calendarmodel", "time value")
    for key in ("timezone", "before", "after"):
        _check(value.get(key, 0) == 0, f"Nonzero time {key} is not representable")
    precision = value["precision"]
    _check(type(precision) is int and 0 <= precision <= 14, "Invalid time precision")
    date = value["time"]
    _check(isinstance(date, str) and re.fullmatch(r"[+-]\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", date),
           "Invalid Wikibase time")
    calendar = value["calendarmodel"]
    _check(isinstance(calendar, str) and re.fullmatch(r"http://www.wikidata.org/entity/Q[1-9]\d*", calendar),
           "Unsupported calendar URI")
    suffix = "" if calendar.endswith("/Q1985727") else "/C" + calendar.rsplit("Q", 1)[1]
    return f"{date}/{precision}{suffix}"


def _snaks(mapping, order=None):
    _check(isinstance(mapping, dict), "Expected a property-to-snaks mapping")
    if order is not None:
        _check(isinstance(order, list) and len(order) == len(set(order)) and set(order) == set(mapping),
               "Invalid snak property order")
    for prop in order if order is not None else mapping:
        _id(prop, "P")
        _check(isinstance(mapping[prop], list) and mapping[prop], f"Empty/invalid snak list for {prop}")
        for snak in mapping[prop]:
            _check(snak["property"] == prop, f"Mismatched property in {prop}")
            yield prop, _value(snak)


def serialize_item(item):
    """Return a complete CREATE/LAST block, or raise ExportError; no side effects.

    Accept a WDI object or its get_wd_json_representation() dictionary.
    Only new items are accepted; existing entity IDs must never become new items.
    """
    try:
        data = item if isinstance(item, dict) else item.get_wd_json_representation()
        return _serialize(data)
    except ExportError:
        raise
    except (KeyError, TypeError, AttributeError, ValueError, UnicodeError) as exc:
        raise ExportError(f"Malformed item: {exc}") from exc


def _serialize(data):
    _keys(data, "labels descriptions aliases claims sitelinks id type", "item")
    _check(not data.get("id"), "Existing item IDs are not supported by the new-item exporter")
    _check(data.get("type", "item") == "item", "Only items can be exported")
    _check(not data.get("sitelinks"), "Sitelinks are not supported")
    lines = ["CREATE"]
    for field, prefix in (("labels", "L"), ("descriptions", "D"), ("aliases", "A")):
        mapping = data.get(field, {})
        _check(isinstance(mapping, dict), f"Invalid {field}")
        for lang, values in mapping.items():
            _language(lang)
            values = values if field == "aliases" else [values]
            _check(isinstance(values, list), "Aliases must be a list")
            for term in values:
                _keys(term, "language value", field)
                _check(term["language"] == lang, "Mismatched term language")
                _check(bool(term["value"]), "Empty terms would be interpreted as removal")
                lines.append("\t".join(("LAST", prefix + lang, _text(term["value"]))))
    claims = data.get("claims", {})
    _check(isinstance(claims, dict), "Claims must be a mapping")
    for prop, statements in claims.items():
        _id(prop, "P")
        _check(isinstance(statements, list), "Statements must be a list")
        previous_values = set()
        for claim in statements:
            _keys(claim, "mainsnak type rank qualifiers qualifiers-order references id", "statement")
            _check(not claim.get("id"), "Existing statement IDs cannot be recreated losslessly")
            _check(claim.get("type", "statement") == "statement", "Unexpected statement type")
            snak = claim["mainsnak"]
            _check(snak["property"] == prop, "Mismatched statement property")
            rank = claim.get("rank", "normal")
            _check(rank in ("normal", "preferred", "deprecated"), f"Unsupported rank: {rank}")
            cells = ["LAST", prop, _value(snak)]
            # QS3 otherwise merges separate statements with the same value.
            # This preserves statement boundaries; it is NOT document filtering.
            if cells[2] in previous_values:
                cells[0] = "+LAST"
            previous_values.add(cells[2])
            if rank != "normal":
                cells.append({"preferred": "R+", "deprecated": "R-"}[rank])
            for key, value in _snaks(claim.get("qualifiers", {}), claim.get("qualifiers-order")):
                cells.extend((key, value))
            refs = claim.get("references", [])
            _check(isinstance(refs, list), "References must be a list")
            for index, ref in enumerate(refs):
                _keys(ref, "snaks snaks-order hash", "reference")
                _check(bool(ref["snaks"]), "Empty reference cannot be preserved")
                for j, (key, value) in enumerate(_snaks(ref["snaks"], ref.get("snaks-order"))):
                    cells.extend((("!" if index > 0 and j == 0 else "") + "S" + key[1:], value))
            lines.append("\t".join(cells))
    _check(len(lines) > 1, "Refusing to export an empty item")
    result = "\n".join(lines) + "\n"
    result.encode("utf-8")
    return result


def _document_id(data):
    try:
        return data["claims"]["P8433"][0]["mainsnak"]["datavalue"]["value"]
    except (KeyError, IndexError, TypeError):
        return None


def _atomic_text(path, write):
    """Replace the target only after successful writing; cleanup on failure."""
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            write(stream)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def export_docs(items, output_path, *, report_path=None, filtered_documents=(), warnings=()):
    """Stream whole validated items to UTF-8 V1 commands plus a JSON report.

    Reject only unrepresentable items, continue with the remainder. File I/O and
    iterator failures propagate; a failed run does not replace the output file.
    No duplicate checking, authentication or network access is performed.
    """
    output = Path(output_path)
    report_file = Path(report_path) if report_path is not None else Path(str(output) + ".report.json")
    _check(output.resolve() != report_file.resolve(), "Output and report paths must differ")
    filtered = list(filtered_documents)
    report = {"format": "QuickStatements 3 / V1", "processed": 0, "exported": 0,
              "filtered": len(filtered), "rejected": 0, "filtered_documents": filtered,
              "warnings": list(warnings), "errors": [],
              "existing": sum(x.get("category") == "existing" for x in filtered),
              "duplicates": sum(x.get("category") == "duplicate" for x in filtered),
              "invalid": sum(x.get("category") not in ("existing", "duplicate") for x in filtered)}

    def write(stream):
        for index, item in enumerate(items, 1):
            report["processed"] += 1
            data = None
            try:
                data = item if isinstance(item, dict) else item.get_wd_json_representation()
                block = serialize_item(data)
            except (ExportError, KeyError, TypeError, AttributeError, ValueError) as exc:
                report["rejected"] += 1
                report["errors"].append({"index": index, "document_id": _document_id(data), "reason": str(exc)})
                continue
            stream.write(block)
            report["exported"] += 1

    _atomic_text(output, write)
    report["input"] = report["processed"] + report["filtered"]
    _atomic_text(report_file, lambda f: json.dump(report, f, ensure_ascii=False, indent=2))
    return report
