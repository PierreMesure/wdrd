# Wdrd → QuickStatements 3

Den här versionen återanvänder Wdrd:s hämtning och transformation men kan skriva
lokala QuickStatements-filer för manuell import. Export kräver ingen
Wikidata-inloggning och skriver aldrig till Wikidata.

Skriptet är inte bundet till ett visst riksmöte. Du väljer riksmöte med
`--session` och dokumenttyp med `--doc-type`. Förutsättningarna för nya
riksmöten beskrivs nedan.

## Installation

Testat med Python 3.12 och WikidataIntegrator 0.9.30. Kör i projektmappen:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

På Windows kan du använda PowerShell utan att aktivera miljön:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
```

I kommandona nedan används `python` för en aktiverad miljö. På Windows kan du
ersätta `python` med `.\.venv\Scripts\python.exe`.
WikidataIntegrator behöver `pkg_resources`; därför begränsas setuptools till `<81`.

## Välj riksmöte och dokumenttyp

CLI stöder `mot` (motioner), `prop` (propositioner), `ip` (interpellationer)
och `fr` (skriftliga frågor). Dokumenttypen väljs vid varje körning.

Kontrollera att riksmötet finns i `sessions` i `wdrd/config.py`. I denna version
finns bland annat följande poster:

```python
    "2025/26": "Q136186928",
    "2026/27": "Q141500916",
```

Dessa QID:n avser **riksmöten**, inte dokumentserier. För ett nytt riksmöte
lägger du till en motsvarande post i den befintliga `sessions`-ordboken.
Behåll de andra posterna. Använd riksmötets beteckning som den anges i
Riksdagens data, exempelvis `2026/27`; koden normaliserar inte olika skrivsätt.

Dokumentserien slås upp automatiskt i Wikidata med hjälp av riksmötet och
`config.doc_types`. Serien måste finnas och kunna hittas med dessa påståenden:

- `P17`: Sverige (`Q34`).
- `P361`: det valda riksmötets QID.
- `P2670`: dokumenttypen, exempelvis motion (`Q452237`) eller proposition (`Q686822`).

Du behöver alltså inte lägga in särskilda `if`-satser eller hårdkoda seriens QID
i `sparql.py` för varje nytt riksmöte. En post i `sessions` räcker på kodsidan
för redan stödda dokumenttyper, förutsatt att motsvarande serie kan hittas i
Wikidata och dokumenten finns i Riksdagens data. Uppslaget tar första träffen;
om ingen serie hittas avbryts körningen.

## 1. Ta ut befintliga P8433-värden manuellt

Gör detta inför varje import: kontrollera manuellt vad som redan finns i
Wikidata och exportera resultatet som UTF-8 CSV (eller TSV). Spara filen som
`befintliga.csv` i projektmappen, eller ange dess sökväg i kommandot. Skriptet
skapar eller uppdaterar inte denna lista åt dig.

Exempel på filformat:

```csv
document_id,qid
H9021,Q123456
H9022,Q234567
```

Värdena ovan visar bara formatet. **Använd din verkliga lista.** `qid` är frivilligt:

```csv
document_id
H9021
H9022
```

Kolumnen får också heta `P8433` eller `p8433`. `item` accepteras som alternativ
till `qid`, även med fullständig Wikidata-URI från en SPARQL-export.
Identifierare behandlas som text, inklusive inledande nollor. Matchningen är exakt
och skiftlägeskänslig. Excel får inte konvertera identifierarna till tal.

Exempel på fråga att köra **manuellt** i Wikidata Query Service och sedan exportera
som CSV:

```sparql
SELECT ?item ?document_id WHERE {
  ?item wdt:P8433 ?document_id .
}
```

Listan måste täcka de dokument som kan ingå i din import. Om frågan blir för tung
kan du begränsa den till den aktuella dokumentserien. Wdrd kör inte frågan åt dig.
Motstridiga QID-mappningar stoppar körningen. Upprepade rader ger rapportvarningar.
Enbart kolumnrubrik är en giltig tom lista, men skyddar då inte mot befintliga objekt.

## 2. Hämta, filtrera, transformera och exportera

Välj riksmöte, dokumenttyp och ett passande namn på utfilen. Följande är
exempel, inte fasta inställningar.

Motioner för riksmötet 2026/27:

```sh
python -m wdrd --session 2026/27 --doc-type mot --existing-documents befintliga.csv --output motioner-2026-27.qs
```

Propositioner för riksmötet 2025/26:

```sh
python -m wdrd --session 2025/26 --doc-type prop --existing-documents befintliga.csv --output propositioner-2025-26.qs
```

Samma motionsexempel i Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m wdrd --session 2026/27 --doc-type mot --existing-documents befintliga.csv --output motioner-2026-27.qs
```

För en annan kombination ändrar du `--session`, `--doc-type` och filnamnet
under `--output`. Kontrollera konfigurationen och gör en ny export av
befintliga P8433-värden som täcker den planerade importen.

Listan valideras före hämtning. Befintliga P8433-värden och upprepade dokument i
samma körning filtreras bort före transformation. Ogiltiga dokument filtreras
fortfarande enligt Wdrd:s regler. Den gamla SPARQL-kontrollen av befintliga
**dokument** anropas inte när den lokala listan används.

Övriga uppslag för personer, serier och propositionskopplingar finns kvar.
WikidataIntegrator kan också hämta egenskapsmetadata. Hela hämt-/transformationsflödet
är alltså inte SPARQL-fritt. Fel i dessa tidigare steg stoppar körningen innan
exporten påbörjas; de ska inte förväxlas med dokument som avvisas av serialiseringen.

En medveten körning utan kontroll kan göras med `--skip-existing-check` i stället
för `--existing-documents`. CLI kräver ett av dessa alternativ för livehämtning.

## 3. Läs rapporten och importera manuellt

Exporten skriver till sökvägen du anger med `--output`. Om du bara anger ett
filnamn hamnar filen i mappen där du kör kommandot. Rapporten får som standard
samma filnamn med `.report.json` tillagt. Motionsexemplet ovan ger alltså
`motioner-2026-27.qs` och `motioner-2026-27.qs.report.json`.
Rapporten visar exporterade, filtrerade och avvisade dokument, med kategorier för
befintliga, upprepade och ogiltiga dokument samt felorsaker och listvarningar.
Exitkod `0` betyder inga exportavvisningar, `2` betyder avvisningar eller argumentfel.
Läs alltid rapporten: en körning kan exportera korrekta dokument och avvisa andra.

I [QuickStatements 3](https://qs-dev.toolforge.org/): välj **New batch → V1**, klistra
in `.qs`-filens innehåll och granska förhandsvisningen. Filen är UTF-8 utan BOM,
med riktiga tabulatorer, ett kommando per rad och ingen rubrikrad. Välj inte CSV.
Ett nytt objekt börjar med `CREATE` och följs av `LAST`-kommandon.

**CREATE skapar nya objekt.** V3:s hantering av dubbla påståenden ersätter inte
kontrollen av befintliga P8433-objekt. En gammal eller ofullständig lista, eller
upprepad import av samma fil, kan fortfarande skapa dubbletter.

## API-exempel

```python
from wdrd import extract_docs, prepare_docs, transform_docs, export_docs

session = '2026/27'  # Välj ett riksmöte som finns i config.sessions.
doc_type = 'mot'     # Välj dokumenttyp.
output = f"{doc_type}-{session.replace('/', '-')}.qs"

raw = extract_docs(session, doc_type)
collection = prepare_docs(raw, existing_documents='befintliga.csv')
items = transform_docs(collection)
report = export_docs(
    items,
    output,
    filtered_documents=collection.filtered_documents,
    warnings=collection.warnings,
)
print(report)
```

`prepare_docs(raw)` behåller den befintliga SPARQL-filtreringen för tidigare
användare. `prepare_docs(raw, remove_existing=False)` hoppar uttryckligen över den.
En angiven lokal lista ersätter alltid SPARQL-filtreringen.

## Prova exporten helt offline

Det här kan köras direkt från projektmappen med enbart Pythons standardbibliotek:

```sh
python -m wdrd --items-json examples/transformed-items.json --output demo.qs
```

Exemplet är **syntetiskt och ska inte importeras i Wikidata**. Det ger två
exporterade och ett avvisat dokument (exitkod 2). Det sista har typografiska
citattecken som QS3 skulle ändra. Referensdatumet i fixturen är låst till 2026-09-22.
JSON-läget tar redan transformerade objekt; eventuell P8433-filtrering görs i
`prepare_docs`, inte i serialiseraren.

## Tester och formatbegränsningar

```sh
python -m pytest -q
```

Se [docs/quickstatements.md](docs/quickstatements.md) för stödda värden, textfall
som avvisas, referensgrupper, datum och kommandon för att köra mot QS3:s faktiska
parser. Se [docs/verification.md](docs/verification.md) för testresultat.

## Uttrycklig direktuppladdning

Den tidigare funktionen `load_docs(items)` finns kvar och loggar in först när den
anropas. Den använder miljövariablerna `WD_USERNAME` och `WD_PASSWORD`.
Varken paketimport, export-CLI eller `export_docs()` anropar denna funktion.

Wdrd:s befintliga dokumenttyper och transformation är i övrigt oförändrade.
CLI exponerar `mot`, `prop`, `ip` och `fr`, vilka har beskrivningslogik i
`wd_item.py`. Befintliga begränsningar i Riksdagens parser och uppslag kvarstår.
