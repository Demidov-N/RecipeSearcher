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
import spacy

from scripts.generating_synonyms import SYNONYMS_OUTPUT_PATH
import shelve
from tqdm import tqdm
from pprint import pprint

CONTENT_INDEX = 'indexes/content'
INGREDIENT_INDEX = 'indexes/ingredients_pretokenized'
INGREDIENT_STATS = 'indexes/stats/ingredients_pretokenized.json'
INGREDIENT_SYNONYMS = 'files/other/synonyms.json'
RECIPE_SHELVES_PATH = 'files/foodrecipes_shelves/foodrecipes_shelves.db'

class RecipeInfoRetrieval:
    def __init__(self, recipe_path):
        self.recipe_path = recipe_path
        
    def open(self):
        self.shelf = shelve.open(self.recipe_path)
        return self
            
    def get_recipe(self, recipe_id):
        recipe = self.shelf.get(recipe_id)
        return recipe
    
    def close(self):
        self.shelf.close()

class LuceneCustomRecipeReader(LuceneIndexReader):
    """Custom Lucene index reader for recipe search. The only addition is that every time the required
    methods are called, we are going to first process the recipe into the undercores, bacuse by default the 
    Anserini is not supporting full phrase indexing """
    
    def __init__(self, index_path):
        super().__init__(index_path)
        self.nlp = spacy.load("en_core_web_sm")
    
    def _preprocess_ingredient(self, ingredient):
        ingredient = [token.lemma_.lower() for token in self.nlp(ingredient) if not token.is_stop and not token.is_punct]
        return "_".join(ingredient)
    
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
        ingredients = list(set(ingredients))  

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
            
    def _bm25search_ingredients(self, ingredients_list, ingredient_weights = None, 
                                reader = None, docinfo = None, 
                                k=1000, k1=1.5, b=0.75, coverage_alpha = 1):
        N = self.ingredient_searcher.num_docs
        dl = np.array(self.stats['dl'])
        avgdl = self.stats['avgdl']

        terms = ingredients_list

        rows, cols, data = [], [], []
        df = np.zeros(len(terms), dtype=float)

        for j, term in enumerate(terms):
            postings = reader.get_postings_list(term, analyzer=None)
            if postings is None:
                print("No postings for term:", term)
                df[j] = 0
                rows.append(0)
                cols.append(j)
                data.append(0)
            else:
                df[j] = len(postings)
                for posting in postings:
                    rows.append(posting.docid)
                    cols.append(j)
                    data.append(posting.tf)

        idf = np.log((N - df + 0.5) / (df + 0.5) + 1.0)
        if ingredient_weights is not None:
            w = np.array(ingredient_weights)
            idf = idf * w    
        

        tf_sparse = csr_matrix((data, (rows, cols)), shape=(N, len(terms)), dtype=float)

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

        if k == "all":
            k = np.sum(adjusted_scores > 0)
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
    def __init__(self, content_path, ingredient_path, index_stats_path, synonym_path = None, recipe_path = None):
        self.ingredient_searcher = IngredientSearcher(ingredient_path, index_stats_path, synonym_path)
        self.content_searcher = RecipeSearcher(content_path)
        if recipe_path is not None:
            self.recipe_reader = RecipeInfoRetrieval(recipe_path)
        else:
            self.recipe_reader = None

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
    
    def _filter_by(self, recipe_results, comparison_key, range):
        # Filter the results by the given range
        filtered_results = []
        for recipe in recipe_results:
            if isinstance(comparison_key, str):
                recipe_value = float(recipe[2].get(comparison_key, None))
            else:
                recipe_value = recipe[2][comparison_key[0]]
                for key in comparison_key[1:]:
                    recipe_value = recipe_value.get(key, None)
            if recipe_value is not None and range[0] <= recipe_value <= range[1]:
                filtered_results.append(recipe)
        return filtered_results


    # Does a search and returns combined results
    # Simple = sum of sigmoid of sub scores is score
    def search(self, ingredients_str="", keywords_str="", k=1000, nsyms=5, ranking='simple', return_full_recipes=False,
               cooking_range=None, calories_range=None, serving_size_range=None):
        ingredient_results = None
        keyword_results = None
        if ingredients_str == "" and keywords_str == "":
            raise ValueError("Both ingredients and keywords cannot be empty")
        if keywords_str == "":
            ingredient_results = self._convert_scores(self.ingredient_searcher.search_ingredients(ingredients_str, k, nsyms))
            ingredient_results = sorted([(ing, ingredient_results[ing]['score']) for ing in ingredient_results], key=lambda x: x[1], reverse=True)
            return ingredient_results
        elif ingredients_str == "":
            keyword_results = self._convert_scores(self.content_searcher.dirichlet_search(keywords_str, k=k))
            keyword_results = sorted([(ing, keyword_results[ing]['score']) for ing in keyword_results], key=lambda x: x[1], reverse=True)
            return keyword_results
        
        ingredient_results = self._convert_scores(self.ingredient_searcher.search_ingredients(ingredients_str, k*10, nsyms))
        keyword_results = self._convert_scores(self.content_searcher.dirichlet_search(keywords_str, k=k*10))
        top_k = []
        match ranking:
            case 'simple':
                for key in set(list(ingredient_results.keys()) + list(keyword_results.keys())):
                    bisect.insort(top_k, (key, ingredient_results[key]['score'] + keyword_results[key]['score']), key=lambda x:x[1])
                    if len(top_k) > k:
                        top_k.pop(0)
            case _:
                for key in set(list(ingredient_results.keys()) + list(keyword_results.keys())):
                    ingredient_results_key = ingredient_results.get(key, {'score': 0, 'rank': 1})
                    keyword_results_key = keyword_results.get(key, {'score': 0, 'rank': 1})
                    ingr_score = ingredient_results_key['score'] / ingredient_results_key['rank']
                    keyword_score = keyword_results_key['score'] / keyword_results_key['rank']
                    bisect.insort(top_k, (key, ingr_score + keyword_score), key=lambda x:x[1])
                    if len(top_k) > k:
                        top_k.pop(0)
        top_k.reverse()
        top_k = top_k[:k]
        if return_full_recipes or cooking_range is not None or calories_range is not None or serving_size_range is not None:
            if self.recipe_reader is None:
                raise ValueError("Recipe reader is not set, cannot return full recipes")
            # get the full recipe for each recipe id and append it to the top_k list
            self.recipe_reader.open()
            for i in range(len(top_k)):
                recipe = self.recipe_reader.get_recipe(top_k[i][0])
                if recipe is not None:
                    top_k[i] = (top_k[i][0], top_k[i][1], recipe)
                else:
                    top_k[i] = (top_k[i][0], top_k[i][1], None)
            self.recipe_reader.close()
            # filter the results by the given ranges
            if cooking_range is not None:
                top_k = self._filter_by(top_k, 'total_time', cooking_range)
            if calories_range is not None:
                top_k = self._filter_by(top_k, 'calories', calories_range)
            if serving_size_range is not None:
                top_k = self._filter_by(top_k, 'yields', serving_size_range)
        return top_k
    
# run a trial ingredient searcher

if __name__ == "__main__":
    
    ingredient_searcher = CustomRecipeSearcher(CONTENT_INDEX, INGREDIENT_INDEX, INGREDIENT_STATS, synonym_path=INGREDIENT_SYNONYMS, 
                                                recipe_path=RECIPE_SHELVES_PATH)
    
    result = ingredient_searcher.search(ingredients_str='chicken breast, parmesan',
                                        keywords_str='quick', k=100, ranking='rrf', cooking_range=(0, 300))
    
    pprint(result)