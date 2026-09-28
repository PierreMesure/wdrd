"""Read manually exported P8433 identifiers without any Wikidata lookup."""
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ExistingDocuments:
    mapping: Dict[str, Optional[str]] = field(default_factory=dict)
    warnings: List[dict] = field(default_factory=list)


def document_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9]+", value):
        raise ValueError(f"Invalid P8433 document identifier: {value!r}")
    return value


def read_existing_documents(path):
    """Read CSV/TSV as UTF-8 (optional BOM); never coerce IDs to numbers.

    Required column: document_id or P8433. Optional QID column: qid or item
    (the latter also accepts a Wikidata entity URI from a SPARQL CSV export).
    Repeated identical rows are reported; conflicting QIDs reject the file.
    """
    result = ExistingDocuments()
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        header = stream.readline()
        stream.seek(0)
        reader = csv.DictReader(stream, delimiter="\t" if "\t" in header else ",")
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ValueError("Duplicate CSV column names")
        id_cols = [x for x in ("document_id", "P8433", "p8433") if x in fields]
        qid_cols = [x for x in ("qid", "item") if x in fields]
        if len(id_cols) != 1 or len(qid_cols) > 1:
            raise ValueError("Expected one document_id/P8433 column and at most one qid/item column")
        for row in reader:
            line = reader.line_num
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Malformed CSV row at line {line}")
            ident = document_id(row[id_cols[0]].strip())
            qid = row[qid_cols[0]].strip() if qid_cols else ""
            if qid.startswith(("http://www.wikidata.org/entity/", "https://www.wikidata.org/entity/")):
                qid = qid.rsplit("/", 1)[1]
            if qid and not re.fullmatch(r"Q[1-9]\d*", qid):
                raise ValueError(f"Invalid QID at line {line}: {qid!r}")
            qid = qid or None
            if ident in result.mapping:
                previous = result.mapping[ident]
                if previous and qid and previous != qid:
                    raise ValueError(f"Conflicting QIDs for {ident}: {previous} and {qid} (line {line})")
                result.warnings.append({"line": line, "document_id": ident, "reason": "Repeated identifier in local list"})
                qid = qid or previous
            result.mapping[ident] = qid
    return result
