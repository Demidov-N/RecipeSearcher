import json
import math
import numpy as np
from tqdm import tqdm

from pyserini.index.lucene import LuceneIndexReader
from sentence_transformers import SentenceTransformer, util


INDEX_DIR = 'indexes/ingredients_pretokenized'
RAW_RECIPES_PATH = 'files/raw/foodrecipes.json'     # optional, if you want to inspect
SYNONYMS_OUTPUT_PATH = 'files/other/synonyms.json'
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# filtering parameters
TF_CUTOFF = 1     # keep ingredients with df > TF_CUTOFF
ALPHA = 0.2   # exponent for TF weighting (0 = ignore TF)
SIM_CUTOFF = 0.6   # zero out sims below this
MIN_SIM = 0.5   # additional minimum sim threshold
TOP_K = 100   # how many synonyms to keep per term

class LuceneCustomRecipeReader(LuceneIndexReader):
    """Wrap LuceneIndexReader to replace spaces with underscores on every query."""
    def _preprocess(self, term: str) -> str:
        return term.replace(' ', '_')

    def get_postings_list(self, term, analyzer=None):
        term = self._preprocess(term)
        return super().get_postings_list(term, analyzer=analyzer)

    def get_term_counts(self, term, analyzer=None):
        term = self._preprocess(term)
        return super().get_term_counts(term, analyzer)

    def get_term_freq(self, term, docid, analyzer=None):
        term = self._preprocess(term)
        return super().get_term_freq(term, docid, analyzer)

def build_synonym_dict_numpy(ingredients, embeddings, tf_dict,
                             alpha=0.5, sim_cutoff=0.6, min_sim=0.5, top_k=100):
    # ensure NumPy array
    if hasattr(embeddings, 'cpu'):
        emb = embeddings.cpu().numpy()
    else:
        emb = np.array(embeddings, dtype=np.float32)
    # normalize
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    normalized = emb / norms

    # TF weighting
    log_tf = np.array([math.log(tf_dict.get(w, 0) + 1) for w in ingredients], dtype=np.float32)
    adjusted_tf = log_tf ** alpha

    synonym_dict = {}
    N = len(ingredients)

    for i in tqdm(range(N), desc="Building synonyms"):
        # cosine sims row
        sim_row = normalized[i].dot(normalized.T)

        # apply cutoffs
        mask = (sim_row >= sim_cutoff) & (sim_row >= min_sim)
        weighted = sim_row * adjusted_tf
        weighted[~mask] = 0.0
        weighted[i] = 0.0  # no self

        # pick top_k
        if top_k < N:
            idxs = np.argpartition(weighted, -top_k)[-top_k:]
        else:
            idxs = np.arange(N)
        # sort them descending
        idxs = idxs[np.argsort(weighted[idxs])[::-1]]

        # build list of (term, score, raw_sim)
        candidates = [
            (ingredients[j], float(weighted[j]), float(sim_row[j]))
            for j in idxs if weighted[j] > 0
        ][:top_k]

        synonym_dict[ingredients[i]] = candidates

    return synonym_dict

def main():
    # 1. Read term frequencies from Lucene
    reader = LuceneCustomRecipeReader(INDEX_DIR)
    tf_list = [(t.term.replace('_', ' '), t.df) for t in reader.terms()]
    tf_list.sort(key=lambda x: x[1], reverse=True)

    # filter by cutoff
    tf_dict = {term: df for term, df in tf_list if df > TF_CUTOFF}
    ingredients = list(tf_dict.keys())

    # 2. Encode with SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(ingredients, convert_to_tensor=True)

    # 3. Build synonym dictionary
    synonyms = build_synonym_dict_numpy(
        ingredients, embeddings, tf_dict,
        alpha=ALPHA, sim_cutoff=SIM_CUTOFF,
        min_sim=MIN_SIM, top_k=TOP_K
    )

    # 4. Write to JSON
    with open(SYNONYMS_OUTPUT_PATH, 'w', encoding='utf8') as out:
        json.dump(synonyms, out, ensure_ascii=False, indent=2)

    print(f"✅ Synonyms written to {SYNONYMS_OUTPUT_PATH}")

    # Optional: inspect one example
    example = 'parmesan'
    if example in synonyms:
        print(f"\nTop synonyms for '{example}':")
        for term, score, raw in synonyms[example][:10]:
            print(f"  {term:20s} score={score:.4f} sim={raw:.4f}")

if __name__ == '__main__':
    main()
