import os
import time
from wikidataintegrator import wdi_core, wdi_login


def load_collection(docs) -> None:
    login_instance = wdi_login.WDLogin(
        user=os.environ.get("WD_USERNAME"), pwd=os.environ.get("WD_PASSWORD")
    )
    summary = f"Adding Riksdagen documents with wdrd."

    for doc in docs:
        try:
            doc.write(login_instance, bot_account=False, edit_summary=summary)
        except wdi_core.NonUniqueLabelDescriptionPairError:
            print('NULD Error')
        time.sleep(1)
