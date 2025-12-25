import os
import time
from wikibaseintegrator import wbi_login


WD_USERNAME = os.environ.get("WD_USERNAME")
WD_PASSWORD = os.environ.get("WD_PASSWORD")
login_instance = wbi_login.Login(user=WD_USERNAME, password=WD_PASSWORD)


def load_collection(docs) -> None:
    summary = "Adding Riksdagen documents with wdrd."

    for doc in docs:
        doc.write(login_instance, is_bot=False, summary=summary)
        time.sleep(1)
