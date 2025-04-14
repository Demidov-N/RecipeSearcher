#!/bin/sh
echo "Preparing JSON files for Indexing"
python index.py
echo "Files Prepared, Starting to Index"

python -m pyserini.index.lucene \
  --collection JsonCollection \
  --input files/index_jsons/content \
  --index indexes/content \
  --generator DefaultLuceneDocumentGenerator \
  --threads 1 \
  --storeRaw

python -m pyserini.index.lucene \
  --collection JsonCollection \
  --input files/index_jsons/ingredients \
  --index indexes/ingredients \
  --generator DefaultLuceneDocumentGenerator \
  --threads 1 \
  --storeRaw

#sleep(100)