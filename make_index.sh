#!/bin/sh

python -m pyserini.index.lucene \
  --collection JsonCollection \
  --input content \
  --index indexes/content \
  --generator DefaultLuceneDocumentGenerator \
  --threads 1

python -m pyserini.index.lucene \
  --collection JsonCollection \
  --input ingredients \
  --index indexes/ingredients \
  --generator DefaultLuceneDocumentGenerator \
  --threads 1

sleep(100)