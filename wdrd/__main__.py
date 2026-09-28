"""Export CLI. There is intentionally no upload command here."""
import argparse
import json
from pathlib import Path

from . import export_docs, extract_docs, prepare_docs, transform_docs


def main():
    parser = argparse.ArgumentParser(description="Export Wdrd to QuickStatements 3 (V1)")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--session", help="Riksdag session, e.g. 2024/25")
    source.add_argument("--items-json", type=Path, help="Offline array of transformed WDI item JSON")
    parser.add_argument("--doc-type", default="mot", choices=("mot", "prop", "ip", "fr"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    check = parser.add_mutually_exclusive_group()
    check.add_argument("--existing-documents", type=Path, help="Local CSV/TSV with document_id (P8433) and optional qid")
    check.add_argument("--skip-existing-check", action="store_true", help="Explicitly allow new CREATE blocks without checking existing documents")
    args = parser.parse_args()
    filtered = []
    warnings = []
    if args.items_json:
        if args.existing_documents or args.skip_existing_check:
            parser.error("Existing-document filtering is for --session; --items-json contains already transformed items")
        with args.items_json.open(encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            parser.error("--items-json must contain a JSON array of transformed items")
    else:
        if not args.existing_documents and not args.skip_existing_check:
            parser.error("Use --existing-documents FILE or explicitly --skip-existing-check")
        # Validate the manual list before making any network calls.
        from .existing import read_existing_documents
        try:
            existing = read_existing_documents(args.existing_documents) if args.existing_documents else None
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        docs = extract_docs(args.session, args.doc_type)
        collection = prepare_docs(docs, remove_existing=False, existing_documents=existing)
        items = transform_docs(collection)
        filtered = collection.filtered_documents
        warnings = collection.warnings
    report = export_docs(items, args.output, report_path=args.report, filtered_documents=filtered, warnings=warnings)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
