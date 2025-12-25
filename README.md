## Get started

This repository contains code for importing data from Riksdagen to Wikidata. To run the code in this repo, you need to setup authentication as per https://github.com/SuLab/WikidataIntegrator. See the `test.ipynb` notebook to get started.

There are four main functions:

- `extract_docs` downloads documents from the Riksdagen API.
- `prepare_docs` takes the raw documents and does some basic cleaning, returning a `DocumentCollection`.
- `transform_docs` takes the `DocumentCollection` and returns a list of WikidataIntegrator items ready to be loaded to Wikidata.
- `load_docs` loads the prepared and transformed documents to Wikidata.

## Supported document types
- <s>Motion</s>
- <s>Proposition</s>
- <s>Interpellation</s>
- <s>Skriftlig fråga</s>
- Protokoll
- Utskottsbetänkande
- Utredningsbetänkande
- Kommittédirektiv
- Lag

## Create a bot password on Wikidata

- Create a Wikidata bot password by going to [this page](https://www.wikidata.org/wiki/Special:BotPasswords). This will enable the script to edit on your behalf. The name should look like *MyUsername@MyBotPasswordName*.

- Create an *.env* file by copying the template and replace the two environment variables with your newly created Wikidata credentials

  ```shell
  cp .env.example .env
  ```

  ```env
  WIKIDATA_USERNAME=MyUsername@MyBotPasswordName
  WIKIDATA_PASSWORD=the-password-i-was-given
  ```

## Get started, detailed instructions

- Install [uv](https://docs.astral.sh/uv/) to manage Python and the project's dependencies
- Create a new Python environment, activate it and install the dependencies

  ```shell
  uv venv
  source .venv/bin/activate
  uv pip install .
  ```
