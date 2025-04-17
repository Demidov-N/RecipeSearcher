import json
from pyserini.search.lucene import LuceneSearcher
from pyserini.index.lucene import LuceneIndexReader
from tqdm import tqdm
import os

index_path = 'indexes/ingredients_pretokenized'
stats_path = 'indexes/stats/ingredients_pretokenized.json'

def generate_index_stats(index_dir: str,
                         output_json_path: str):
    """
    Scans the Pyserini index at `index_dir`, uses `reader.analyze()` to
    tokenize each document’s contents, and writes out a JSON with:
      - dl:   [doc_length_0, doc_length_1, …]
      - iids: [external_id_0, external_id_1, …]
      - avgdl: float
    """
    searcher = LuceneSearcher(index_dir)
    reader = LuceneIndexReader(index_dir)
    N = searcher.num_docs

    # Prepare containers
    dl   = [0] * N
    iids = [None] * N

    # One pass over all docs
    for docid in tqdm(range(N)):
        doc       = searcher.doc(docid)
        contents  = json.loads(doc.raw())['contents']
        tokens    = reader.analyze(contents)      # your analyzer
        dl[docid] = len(tokens)
        iids[docid] = doc.docid()                # external identifier

    avgdl = sum(dl) / N if N > 0 else 0.0

    # Dump to JSON (convert everything to plain Python types)
    stats = {
        "avgdl": avgdl,
        "dl":   dl,
        "iids": iids
    }
    
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as out:
        json.dump(stats, out, ensure_ascii=False, indent=2)

    print(f"[generate_index_stats] wrote stats for {N} docs → {output_json_path}")
    
if __name__ == "__main__":
    generate_index_stats(index_path, stats_path)
    print(f"Index statistics saved to {stats_path}.")