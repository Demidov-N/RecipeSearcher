from re import S
#from typing import override
import numpy as np
from pyserini.index import LuceneIndexReader
from pyserini.search.lucene import LuceneSearcher
import bisect # https://docs.python.org/3/library/bisect.html
import json
import math
from collections import defaultdict
from scipy.sparse import csr_matrix

class LuceneCustomRecipeReader(LuceneIndexReader):
    """Custom Lucene index reader for recipe search. The only addition is that every time the required
    methods are called, we are going to first process the recipe into the undercores, bacuse by default the 
    Anserini is not supporting full phrase indexing """
    
    def _preprocess_ingredient(self, ingredient):
        return ingredient.replace(' ', '_')
    
    #@override
    def get_postings_list(self, term, analyzer=None):
        term = self._preprocess_ingredient(term)
        return super().get_postings_list(term, analyzer=analyzer)
    
    #@override
    def get_term_counts(self, term, analyzer = None):
        term = self._preprocess_ingredient(term)
        return super().get_term_counts(term, analyzer)
    
class IngredientSearcher:
    def __init__(self, ingredient_path, index_stats_path, synonym_path = None):
        
        self.ingredient_reader = LuceneCustomRecipeReader(ingredient_path)
        self.ingredient_searcher = LuceneSearcher(ingredient_path)
        with open(index_stats_path, 'r') as f:
            self.stats = json.load(f)
        
        if synonym_path is not None:
            with open(synonym_path, 'r') as f:
                self.synonyms = json.load(f)    
        else:
            self.synonyms = None

    def search_ingredients(self, ingredients_string, k=1000, nsyms=5):
        # 1) Parse the user’s comma‑separated ingredients
        ingredients = [ing.strip() for ing in ingredients_string.split(',')]

        # 2) Build one group per original ingredient
        groups = {}
        for ing in ingredients:
            # start with the ingredient itself at weight=1
            syns = [(ing, 1.0)]
            # add up to nsyms synonyms (term, score)
            if self.synonyms is not None and ing in self.synonyms:
                for term, _, score in self.synonyms[ing][:nsyms]:
                    syns.append((term, float(score)))
            groups[ing] = syns

        # 3) Normalize each group so its weights sum to 1.0
        terms, weights = [], []
        for syns in groups.values():
            total = sum(w for _, w in syns)
            for term, w in syns:
                terms.append(term)
                weights.append(w / total if total > 0 else 0.0)

        # 4) Now call your BM25, passing in *aligned* terms & weights
        return self._bm25search_ingredients(
            ingredients_list=terms,
            ingredient_weights=weights,
            reader=self.ingredient_reader,
            docinfo=self.stats,
            k=k
        )
            
    def _bm25search_ingredients(self, ingredients_list, ingredient_weights = None, reader = None, docinfo = None, 
                                k=1000, k1=1.5, b=0.75, coverage_alpha = 1):
        # 1) Basic stats
        N = self.ingredient_searcher.num_docs
        dl = np.array(self.stats['dl'])
        avgdl = self.stats['avgdl']

        # dedupe query terms
        terms = list(dict.fromkeys(ingredients_list))

        # 2) Gather postings + compute df
        rows, cols, data = [], [], []
        df = np.zeros(len(terms), dtype=float)

        for j, term in enumerate(terms):
            postings = reader.get_postings_list(term, analyzer=None)
            df[j] = len(postings)
            for posting in postings:
                rows.append(posting.docid)
                cols.append(j)
                data.append(posting.tf)

        # 3) IDF
        idf = np.log((N - df + 0.5) / (df + 0.5) + 1.0)
        if ingredient_weights is not None:
            w = np.array(ingredient_weights)
            idf = idf * w    
        

        # 4) Build sparse TF matrix
        tf_sparse = csr_matrix((data, (rows, cols)), shape=(N, len(terms)), dtype=float)

        # 5) BM25 scoring
        scores = np.zeros(N, dtype=float)
        for j in range(len(terms)):
            tf_col = tf_sparse[:, j].toarray().ravel()
            numer   = tf_col * (k1 + 1.0)
            denom   = tf_col + k1 * (1.0 - b + b * (dl / avgdl))
            scores += idf[j] * (numer / denom)
        
        match_mask = (tf_sparse > 0)
        matched_counts = match_mask.sum(axis=1).A1    # .A1 to get a flat NumPy array of shape (N,)
        
        coverage = matched_counts / np.sum(ingredient_weights)
        
        adjusted_scores = scores * (1 + coverage_alpha * coverage)


        # 6) Top‑k
        topk_idx   = np.argpartition(-adjusted_scores, k)[:k]
        topk_scores = adjusted_scores[topk_idx]
        order      = np.argsort(-topk_scores)

        return [
            (docinfo['iids'][topk_idx[i]], float(topk_scores[i]))
            for i in order
        ]

class RecipeSearcher:
    def __init__(self, content_path):
        #self.ingredient_reader = LuceneIndexReader(ingredient_path)
        self.content_reader = LuceneIndexReader(content_path)
        #self.ingredient_searcher = LuceneSearcher(ingredient_path)
        self.content_searcher = LuceneSearcher(content_path)
        self.content_docinfo = []
        for i in range(self.content_searcher.num_docs):
            self.content_docinfo.append({
                'n': len(self.content_reader.analyze(json.loads(self.content_searcher.doc(i).raw())['contents'])),
                'id': i,
                'iid': self.content_searcher.doc(i).docid()
            })

    # Query likelihood model with dirichlet smoothing.
    # Should be run on the keywords part of the query, which is then combined with a custom score from ingredients
    def dirichlet_search(self, query, reader = None, docinfo = None, k=1000):
        # can't directly set these by default, so here's a workaround
        if docinfo is None:
            docinfo = self.content_docinfo
        if reader is None:
            reader = self.content_reader
        searcher = self.content_searcher
        query_terms = reader.analyze(query)
        top_k = []
        mu = np.sum([doc['n'] for doc in docinfo]) / len(docinfo)
        
        # define a list of docs that we want to go over, it should contain at least a single value in the query
        docs = set()
        term_doc_frequencies = {}
        term_c_frequencies = {}
        #print("Retrieving the term frequencies")
        for term in query_terms:
            posting_list = reader.get_postings_list(term, analyzer=None)
            term_c_frequencies[term] = reader.get_term_counts(term, analyzer=None)[1]
            term_doc = {}
            for posting in posting_list:
                docs.add(posting.docid)
                term_doc[posting.docid] = posting.tf
            term_doc_frequencies[term] = term_doc
                
        
        #print("Computing likelihoods")
        top_k = []
        C = reader.stats()['total_terms'] # total number of terms in collection
        for docid in docs:
            single_docinfo = docinfo[docid]
            D = single_docinfo['n'] # number of terms in the document
            score = 0
            for term in query_terms:
                cf = term_c_frequencies[term] # get the document and collection frequency
                # get the term frequency for the term in the document
                tf = term_doc_frequencies[term].get(docid, 0)
                # compute the log likelihood
                score += np.log((tf + mu * cf / C)/ (D + mu))
                
            # get the document external id because this is how the searcher is returning it
            docid_external = searcher.doc(docid).docid()
            # insert the score in the correct position
            bisect.insort(top_k, (docid_external, score), key=lambda x: x[1])
            # remove the first element if the length is greater than k
            if len(top_k) > k:
                top_k.pop(0)
        top_k.reverse()
        # return in the same format as reader.search function
        
        return top_k
    
class CustomRecipeSearcher:
    def __init__(self, content_path, ingredient_path, index_stats_path, synonym_path = None):
        self.ingredient_searcher = IngredientSearcher(ingredient_path, index_stats_path, synonym_path)
        self.content_searcher = RecipeSearcher(content_path)

    # Generic sigmoid function
    def sigmoid(self, x):
        return 1 / (1 + math.exp(-x))
    
    # Convert each result list into dictionary that returns default 0 if key not found, normalize scores with sigmoid
    def _convert_scores(self, scores: list[tuple]):
        res = defaultdict(lambda :{'score': 0, 'rank': 1})
        for i in range(len(scores)):
            x = scores[i]
            res[x[0]] = {
                'score': self.sigmoid(x[1]),
                'rank': i + 1
            }
        return res

    # Does a search and returns combined results
    # Simple = sum of sigmoid of sub scores is score
    def search(self, ingredients_str, keywords_str, k=1000, nsyms=5, ranking='simple'):
        ingredient_results = self._convert_scores(self.ingredient_searcher.search_ingredients(ingredients_str, k, nsyms))
        keyword_results = self._convert_scores(self.content_searcher.dirichlet_search(keywords_str, k=k))
        top_k = []
        match ranking:
            case 'simple':
                for key in set(list(ingredient_results.keys()) + list(keyword_results.keys())):
                    bisect.insort(top_k, (key, ingredient_results[key]['score'] + keyword_results[key]['score']), key=lambda x:x[1])
            case 'rrf':
                for key in set(list(ingredient_results.keys()) + list(keyword_results.keys())):
                    ingr_score = ingredient_results[key]['score'] / ingredient_results[key]['rank']
                    keyword_score = keyword_results[key]['score'] / keyword_results[key]['rank']
                    bisect.insort(top_k, (key, ingr_score + keyword_score), key=lambda x:x[1])
            case _:
                raise ValueError('invalid ranking method')
        top_k.reverse()
        return top_k
    
# run a trial ingredient searcher

if __name__ == "__main__":
    content_index = 'indexes/content'
    index = 'indexes/ingredients_pretokenized'
    stats = 'indexes/stats/ingredients_pretokenized.json'
    ingredients_synonyms = 'files/other/synonyms.json'
    
    ingredient_searcher = CustomRecipeSearcher(content_index, index, stats)#, synonym_path=ingredients_synonyms)
    
    result = ingredient_searcher.search('chicken breast, parmesan', 'quick', k=10, ranking='rrf')
    
    print(result)