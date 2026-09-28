# Verifiering – 2026-09-22

**72 tester passerade**, inklusive 25 tester mot QuickStatements 3:s oförändrade
parser och lokala objektkonstruktion. Se `test-results.txt` för körutdata.

Miljö: Python 3.12, WikidataIntegrator 0.9.30, pandas 3.0.6, pytest 9.1.1,
setuptools 80.10.2. QS3-revision och reproduktionskommandon finns i
`quickstatements.md`. Setuptools begränsas till `<81` eftersom WDI fortfarande
använder `pkg_resources`; dess deprecationsvarning kvarstår.

Verifierat:

- Befintlig Wdrd-transformation till riktiga WDI-objekt, med lokala testuppslag.
- Hela kedjan från DocumentCollection till transformation och export.
- Varje transformerad etikett, beskrivning, huvudvärde, bestämning och referens
  jämförs med vad den riktiga QS3-parsern producerar.
- Flera författare, ordningsnummer, propositionskoppling, separata referensgrupper,
  alias, rankningar och datumprecision med olika kalendrar.
- `CREATE`/`LAST`, `somevalue` och `novalue`, inklusive QS3:s lokala konstruktion
  av ett nytt objekt. Separata påståenden med identiska huvudvärden bevaras.
- UTF-8 och svenska tecken; riskabla strängar avvisas för hela dokumentet.
- Paketimport och offlineexport utan WDI-import, inloggning eller nätverk.
- Import av uppladdningsmodulen skapar ingen session; uttrycklig uppladdningsväg
  använder mockad autentisering i testet, utan någon `.write()`.
- Lokal P8433-lista med CSV/TSV, frivilliga QID:n, inledande nollor och BOM.
- Lokala listan ersätter dokumentens SPARQL-kontroll; ogiltiga dokument filtreras
  fortfarande. Identiska rader rapporteras, konflikter stoppar körningen och
  upprepade dokument i samma körning filtreras bort.
- Rapportens räkning, CLI:s exitkoder och att iteratorfel inte ersätter en
  tidigare exportfil.

Installerbarheten verifierades med `pip install --no-deps -e .` efter separat
installation av testmiljöns runtimeberoenden. En ren fullinstallation med alla
upstreams notebookberoenden har inte körts. Inga nya notebookfunktioner krävs.

## Exempelresultat

`examples/transformed-items.json` skapades från Wdrd:s riktiga transformation av
ett syntetiskt dokument, med två kompletterande testvarianter. Den innehåller
inte verkliga motioner för publicering.

| Resultat | Antal |
|---|---:|
| Behandlade transformerade dokument | 3 |
| Exporterade | 2 |
| Avvisade | 1 |
| Filtrerade före serialisering i detta offlineexempel | 0 |

Avvisningen gäller typografiska dubbla citattecken i `DEMO0003`. Det dokumentet
saknar helt `CREATE`-block i `examples/demo.qs`; de två andra är kompletta.
`examples/demo.qs.report.json` innehåller felorsaken. Den lokala listans filtrering
är verifierad separat i testerna, inklusive befintligt, upprepat och ogiltigt ID.

## Praktiska gränser

Ingen skarp hämtning av en hel riksmötesserie har körts, och inga uppgifter har
skrivits till Wikidata. Liveuppslag, aktuella API-svar, källornas fullständighet,
QS3-tjänstens driftsatta kod och Wikidatas servervalidering är inte verifierade.
Detta är verifierad serialisering och lokal parser-/payloadkompatibilitet,
inte en genomförd import.

Wdrd:s ursprungliga datahämtning och transformation har kvar sina tidigare
begränsningar. Exempelvis beror person- och propositionskopplingar fortfarande
på uppslagen; exporteraren lägger inte till saknade författare eller fält.
