from functools import lru_cache as cache
import os
import pandas as pd
from wikibaseintegrator.wbi_helpers import execute_sparql_query

from . import config

USER_AGENT = f"{os.environ.get('WD_USERNAME')} wdrd (github.com/PierreMesure/wdrd)"


@cache
def get_series_qid(session: str, doc_type: str) -> str:
    session_qid = config.sessions[session]
    doc_type_qid = config.doc_types[doc_type]
    query = (
        "SELECT ?item ?itemLabel WHERE {"
        "?item wdt:P17 wd:Q34 ;"
        f"wdt:P361 wd:{session_qid} ;"
        f"wdt:P2670 wd:{doc_type_qid} ."
        'SERVICE wikibase:label { bd:serviceParam wikibase:language "sv". }}'
    )

    response = execute_sparql_query(query, user_agent=USER_AGENT)
    return response["results"]["bindings"][0]["item"]["value"].split("/")[-1]


@cache
def get_series_docs(session: str, doc_type: str) -> pd.DataFrame:
    series_qid = get_series_qid(session, doc_type)
    doc_type_qid = config.doc_types[doc_type]

    query = (
        "SELECT ?item ?itemLabel ?code ?ref WHERE {"
        f"?item wdt:P31/wdt:P279* wd:{doc_type_qid} ;"
        f"wdt:P179 wd:{series_qid} ;"
        "wdt:P8433 ?code ;"
        "wdt:P1031 ?ref ."
        'SERVICE wikibase:label { bd:serviceParam wikibase:language "sv". }}'
    )
    response = execute_sparql_query(query, user_agent=USER_AGENT)

    items = [
        {
            "item": item["item"]["value"],
            "itemLabel": item["itemLabel"]["value"],
            "code": item["code"]["value"],
            "ref": item["ref"]["value"],
        }
        for item in response["results"]["bindings"]
    ]
    df = pd.DataFrame(items)

    if df.empty:
        return pd.DataFrame({"item": [], "itemLabel": [], "code": [], "ref": []})
    df["item"] = df["item"].str.split("/", expand=True)[4]
    return df


@cache
def get_people() -> pd.DataFrame:
    query = """SELECT ?item ?itemLabel ?code WHERE {
    ?item wdt:P1214 ?code .

    SERVICE wikibase:label { bd:serviceParam wikibase:language "sv". }
    }"""

    response = execute_sparql_query(query, user_agent=USER_AGENT)
    items = [
        {
            "item": item["item"]["value"],
            "itemLabel": item["itemLabel"]["value"],
            "code": item["code"]["value"],
        }
        for item in response["results"]["bindings"]
    ]
    df = pd.DataFrame(items)

    df.item = df.item.str.split("/", expand=True)[4]
    return df
