@echo off
REM ---------------------------------------------
REM  index.bat — Prepare JSON, build Lucene indexes
REM ---------------------------------------------

echo Preparing JSON files for Indexing...
python scripts\index.py

echo.
echo Files prepared. Starting to index content...
echo.

REM Indexing raw content
python -m pyserini.index.lucene ^
  --collection JsonCollection ^
  --input files\index_jsons\content ^
  --index indexes\content ^
  --generator DefaultLuceneDocumentGenerator ^
  --threads 1 ^
  --storeRaw

echo.
echo Indexing ingredients (pre-tokenized)...
echo.

REM Indexing pre-tokenized ingredients
python -m pyserini.index.lucene ^
  --collection JsonCollection ^
  --input files\index_jsons\ingredients_pretokenized ^
  --index indexes\ingredients_pretokenized ^
  --generator DefaultLuceneDocumentGenerator ^
  --threads 1 ^
  --storeRaw ^
  --pretokenized

echo.
echo Generating index statistics...
echo.

python scripts\generate_index_statistics.py

echo.
echo All done!
pause
