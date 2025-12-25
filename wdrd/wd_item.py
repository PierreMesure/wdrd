import simplejson
from datetime import datetime
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.datatypes import (
    ExternalID,
    Time,
    MonolingualText,
    String,
    Item,
    URL,
)
import requests
from . import config as cfg


def create_reference(doc):
    ref = []
    now = datetime.now().strftime("+%Y-%m-%dT00:00:00Z")
    ref.append(ExternalID(value=doc.doc_id, prop_nr="P8433"))
    ref.append(Time(time=now, prop_nr="P813"))
    ref.append(MonolingualText(text=doc.title, language="sv", prop_nr="P1476"))
    return ref


def create_authors(doc):
    if doc.authors is None:
        return None
    ref = create_reference(doc)
    snak_type = "value"
    prop = "P1891" if doc.doc_type == "prop" else "P50"
    signs = []
    over_one = len(doc.authors) > 1
    sign_codes = []
    for i, person in enumerate(doc.authors):
        if person["qid"] in sign_codes:
            continue
        if person["qid"] is None:
            snak_type = "somevalue"
        else:
            snak_type = "value"
        sign_codes.append(person["qid"])
        if over_one:
            sign_qual = String(str(i + 1), prop_nr="P1545")
            obj = Item(
                person["qid"],
                snak_type=snak_type,
                prop_nr=prop,
                references=[ref],
                qualifiers=[sign_qual],
            )
        else:
            obj = Item(
                person["qid"], snak_type=snak_type, prop_nr=prop, references=[ref]
            )
        signs.append(obj)
    return signs


def create_debate(doc):
    if doc.doc_type != "ip":
        return None
    url = f"https://riksdagen.se/api/videostream/get/{doc.doc_id}"
    resp = requests.get(url)
    try:
        data = resp.json()
    except simplejson.JSONDecodeError:
        return None
    video_url = "https://riksdagen.se" + data["videodata"][0]["debateurl"]
    video_qual = URL(video_url, prop_nr="P2699")
    return Item("Q179875", prop_nr="P793", qualifiers=[video_qual])


def create_respondent(doc):
    if doc.respondent:
        ref = create_reference(doc)
        return Item(doc.respondent["qid"], prop_nr="P1817", references=[ref])


def create_descriptions(doc):
    descriptions = {}

    if doc.doc_type == "mot":
        label_date = doc.date[1:5]

        if doc.authors is None:
            descriptions["sv"] = f"motion från {label_date}"
            descriptions["en"] = f"motion from {label_date}"
            return descriptions

        label_name = doc.authors[0]["name"]
        if len(doc.authors) > 1:
            et_al_sv, et_al_en = " m.fl. ", " et al. "
            label_name = label_name.replace("av ", "")
        else:
            et_al_sv = et_al_en = " "
        descriptions["sv"] = f"motion av {label_name}{et_al_sv}från {label_date}"
        descriptions["en"] = f"motion by {label_name}{et_al_en}from {label_date}"
    elif doc.doc_type == "prop":
        descriptions["sv"] = f"proposition i riksdagen från {doc.date[1:11]}"
        descriptions["en"] = f"proposition in the Riksdag from {doc.date[1:11]}"
    elif doc.doc_type == "ip":
        label_author = doc.authors[0]["name"]
        label_respondent = doc.respondent["name"]
        label_date = doc.date[1:11]
        descriptions["sv"] = (
            f"interpellation i riksdagen från {label_author} till {label_respondent}, {label_date}"
        )
        descriptions["en"] = (
            f"interpellation in the Riksdag from {label_author} to {label_respondent}, {label_date}"
        )
    elif doc.doc_type == "fr":
        label_author = doc.authors[0]["name"]
        label_respondent = doc.respondent["name"]
        descriptions["sv"] = (
            f"skriftlig fråga från {label_author} till {label_respondent}"
        )
        descriptions["en"] = (
            f"written question from {label_author} to {label_respondent}"
        )

    return descriptions


def create_jurisdiction():
    return Item(prop_nr="P1001", value="Q34")


def create_title(doc):
    ref = create_reference(doc)
    return MonolingualText(doc.title, language="sv", prop_nr="P1476", references=[ref])


def create_series(doc):
    num_qual = String(value=str(doc.ordinal), prop_nr="P1545")
    series = Item(doc.series, prop_nr="P179", qualifiers=[num_qual])
    return series


def create_lang():
    return Item("Q9027", prop_nr="P407")


def create_date(doc):
    ref = create_reference(doc)
    return Time(doc.date, prop_nr="P577", references=[ref])


def create_legal_ref(doc):
    return String(f"{doc.doc_type}. {doc.session}:{doc.ordinal}", prop_nr="P1031")


def create_copyright():
    det_qual = Item("Q80211245", prop_nr="P459")
    copyright = Item("Q19652", prop_nr="P6216", qualifiers=[det_qual])
    return copyright


def create_resource_links(doc):
    links = []
    html_qual = Item("Q62626012", prop_nr="P2701")
    links.append(URL(doc.html, prop_nr="P953", qualifiers=[html_qual]))

    xml_qual = Item("Q3033641", prop_nr="P2701")
    links.append(URL(doc.xml, prop_nr="P953", qualifiers=[xml_qual]))

    if doc.pdf:
        pdf_qual = Item("Q42332", prop_nr="P2701")
        links.append(URL(doc.pdf, prop_nr="P953", qualifiers=[pdf_qual]))

    return links


def create_riksdagen_id(doc):
    return ExternalID(value=doc.doc_id, prop_nr="P8433")


def create_committee(doc):
    if not doc.committee:
        return None
    ref = create_reference(doc)
    return Item(doc.committee, prop_nr="P7727", references=[ref])


def create_instance_of(doc):
    ref = create_reference(doc)
    if doc.doc_type == "mot":
        return Item(doc.subtype, prop_nr="P31", references=[ref])
    else:
        return Item(cfg.doc_types[doc.doc_type], prop_nr="P31", references=[ref])


def create_cause(doc):
    if doc.cause:
        return Item(doc.cause, prop_nr="P1478")


def create_item(doc):
    data = []

    data.append(create_jurisdiction())
    data.append(create_title(doc))
    data.append(create_series(doc))
    data.append(create_lang())
    data.append(create_date(doc))
    data.append(create_legal_ref(doc))
    data.append(create_copyright())
    data.extend(create_resource_links(doc))
    data.append(create_riksdagen_id(doc))
    data.append(create_instance_of(doc))
    try:
        data.extend(create_authors(doc))
    except TypeError:
        pass
    data.append(create_committee(doc))
    data.append(create_cause(doc))
    data.append(create_respondent(doc))
    data.append(create_debate(doc))

    data = [x for x in data if x is not None]

    wbi = WikibaseIntegrator()
    item = wbi.item.new()
    item.claims.add(claims=data)
    item.labels.set(value=doc.title[:249], language="sv")

    descriptions = create_descriptions(doc)
    item.descriptions.set(value=descriptions["sv"], language="sv")
    item.descriptions.set(value=descriptions["en"], language="en")
    return item
