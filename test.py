from dotenv import load_dotenv

load_dotenv()

from wdrd import extract_docs, prepare_docs, transform_docs, load_docs

docs = extract_docs("2024/25", "prop")

print(type(docs), len(docs))

docs = prepare_docs(docs[0:5])

print(type(docs), len(docs.docs))

docs = transform_docs(docs)

docs = [
    x
    for x in docs
    if x.get_wd_json_representation()["labels"]["sv"]["value"]
    != "Ej avlämnad till riksdagen"
]

print(len(docs))

print(load_docs(docs[0:5]))
