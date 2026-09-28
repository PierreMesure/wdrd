import logging

logging.captureWarnings(True)

from .quickstatements import export_docs


def extract_docs(session: str, doc_type: str) -> list:
    from . import riksdagen
    return riksdagen.get_series_docs(session, doc_type)


def prepare_docs(docs: list, *, remove_existing=True, existing_documents=None):
    from . import document
    collection = document.DocumentCollection(
        docs, remove_existing=remove_existing, existing_documents=existing_documents
    )
    return collection


def transform_docs(collection) -> list:
    from . import wd_item
    items = [wd_item.create_item(x) for x in collection.docs]
    return items


def load_docs(items: list) -> None:
    from . import load
    load.load_collection(items)
