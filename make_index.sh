#!/bin/sh
echo "Preparing JSON files for Indexing"
python scripts/index.py
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
  --input files/index_jsons/ingredients_pretokenized \
  --index indexes/ingredients_pretokenized \
  --generator DefaultLuceneDocumentGenerator \
  --threads 1 \
  --storeRaw \
  --pretokenized 
  
python scripts/generate_index_statistics.py

#sleep(100)