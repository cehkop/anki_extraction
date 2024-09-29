# Exctract collocations from text and add them to Anki. Powered by OpenAI.

## Dependencies
Rye, Anki, AnkiConnect, OpenAI api key

## Installation
1. Copy code
2. docker build -t anki-processor .
3. docker run -p 2341:2341 --network=host anki-processor