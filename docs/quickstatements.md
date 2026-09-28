# Format, källor och begränsningar

Mål: **QuickStatements 3, New batch → V1**, tabulatorseparerad kommandosekvens.
Detta är V1-syntax i v3-programmet, inte den gamla versionen av tjänsten.

Granskad Wdrd-bas: `8e9a8f120ff1def72c0a746c40d653997c15cd4b`.
Granskad QS3-parser: `14ab3b079432096b76b4dfe1bf712b7051f47685`.

Källor:

- https://github.com/PierreMesure/wdrd
- https://meta.wikimedia.org/wiki/QuickStatements_3.0/Documentation/User_guide
- https://github.com/wikimediabrasil/quickstatements3/blob/14ab3b079432096b76b4dfe1bf712b7051f47685/src/core/parsers/v1.py
- https://github.com/wikimediabrasil/quickstatements3/blob/14ab3b079432096b76b4dfe1bf712b7051f47685/src/core/parsers/base.py
- https://github.com/wikimediabrasil/quickstatements3/blob/14ab3b079432096b76b4dfe1bf712b7051f47685/src/core/models.py

## Vad som bevaras

Samtliga etiketter, beskrivningar, alias, påståenden, bestämningar och referenser
från den transformerade representationen behandlas generiskt, utan lista över
vilka egenskaper som ska få följa med. Wdrd:s egen transformation ändras inte.
Exporteraren kan inte återställa uppgifter som Wdrd redan har filtrerat bort.

| Innehåll | Export |
|---|---|
| Objektvärde | `Q123` |
| Sträng, extern identifierare, URL | `"värde"` utan JSON-escaping |
| Enspråkig text | `sv:"text"` |
| Datum | Signerat datum med `/precision` och vid behov `/Ckalendernummer` |
| Bestämning | `Pnummer` och värde på samma rad som påståendet |
| Referens | `Snummer`; första delen i senare referensgrupper använder `!Snummer` |
| Normal rankning | Implicit standard |
| Föredragen/avrådd rankning | `R+` / `R-` i fjärde kolumnen |
| Okänt/inget värde | `somevalue` / `novalue`, även efter `CREATE` med `LAST` |

Om två separata påståenden inom samma objekt har samma egenskap och huvudvärde
används `+LAST` på det senare, så att QS3 inte slår ihop deras bestämningar eller
rankning. Detta bevarar påståendestrukturen och är skilt från kontrollen av redan
befintliga dokument, som görs mot den manuella P8433-listan.

Referenshashar och snakhashar är Wikibase-metadata som beräknas på nytt och blir
inte kommandon. Bestämnings-/referensordning följer befintliga ordningslistor när
sådana finns. Datumens precision och kalender bevaras; tidszon och före-/efter-
osäkerhet måste vara noll eftersom V1-formatet saknar motsvarande fält.

## Uttryckliga avvisningar

Ett enda värde som inte kan representeras gör att hela dokumentet avvisas.
Ingen `CREATE`-rad skrivs för det dokumentet. Övriga dokument kan exporteras.

Det konservativa textstödet avvisar:

- ASCII-dubbelcitattecken och bakstreck: ingen generell säker escaping antas.
- Typografiska dubbla citattecken `“`/`”`: QS3 ersätter dem med ASCII-citattecken.
- Inledande/avslutande whitespace: QS3 tar bort dem.
- Kontrolltecken, tabulatorer, radbrytningar och Unicode-radavgränsare.
- QS3:s interna platshållartext `___QSTS3_PLACEHOLDER___`.

Svenska tecken, apostrofer, bindestreck, pipes, dubbla pipes och kommentarliknande
text inne i stödda citerade strängar har testats. Strängar ändras aldrig för att
passa formatet. Vissa avvisade textkombinationer kan fungera i QS3, men ingår inte
i denna exports verifierade delmängd.

Andra datatyper än dem i tabellen (t.ex. koordinater och kvantiteter), sitelänkar,
befintliga objekt-/påstående-ID:n, okända strukturfält och felaktiga strukturer
avvisas uttryckligen. Dessa datatyper förekommer inte i Wdrd:s granskade
transformation. Stödet för språk är begränsat till bokstavskoder med bindestreck.

Exporten skrivs strömmande ett helt validerat objekt i taget till en temporär
fil; målfilen ersätts först när iteration och skrivning har lyckats. Rapporten
skrivs också atomiskt, men fil och rapport är inte en gemensam transaktion.
Ett rapportskrivfel ger därför undantag och kan lämna en färdig exportfil.
Filer delas inte automatiskt. Dela endast vid nästa `CREATE`, aldrig inne i ett objekt.

## Kör verifiering mot upstream-parsern

Utöver vanliga testberoenden krävs följande för de frivilliga parser-/payloadtesterna
(Python 3.12 användes vid verifieringen):

```sh
git clone https://github.com/wikimediabrasil/quickstatements3.git ../quickstatements3
git -C ../quickstatements3 checkout 14ab3b079432096b76b4dfe1bf712b7051f47685
python -m pip install Django==5.0.9 Authlib==1.3.1 jsonpatch==1.33
QS3_SOURCE=../quickstatements3 python -m pytest -q
```

I PowerShell: sätt `$env:QS3_SOURCE='../quickstatements3'` och kör sedan pytest.
Parserkoden och QS3:s objektkonstruktion används oförändrade; Django konfigureras
lokalt utan databasåtkomst. Tester blockerar HTTP och socketanslutningar.
WDI:s uppslag av egenskapsmetadata ersätts med testdata när transformationsfixturen
skapas. Ingen test kör `.write()` eller en verklig import.

Utan `QS3_SOURCE` hoppas de frivilliga testerna över. Parseracceptans och lokal
objektkonstruktion är verifierade; produktionstjänstens driftsatta revision,
Wikidatas validering och en verklig import är **inte** verifierade.
