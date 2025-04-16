from typing import override
import numpy as np
from pyserini.index import LuceneIndexReader
from pyserini.search.lucene import LuceneSearcher
import bisect # https://docs.python.org/3/library/bisect.html

class LuceneCustomRecipeReader(LuceneIndexReader):
    """Custom Lucene index reader for recipe search. The only addition is that every time the required
    methods are called, we are going to first process the recipe into the undercores, bacuse by default the 
    Anserini is not supporting full phrase indexing """
    
    def _preprocess_ingredient(self, ingredient):
        return ingredient.replace(' ', '_')
    
    @override
    def get_postings_list(self, term, analyzer=None):
        term = self._preprocess_ingredient(term)
        return super().get_postings_list(term, analyzer=analyzer)
    
    @override
    def get_term_counts(self, term, analyzer = None):
        term = self._preprocess_ingredient(term)
        return super().get_term_counts(term, analyzer)
    


class RecipeSearcher:
    def __init__(self, ingredient_path, content_path):
        self.ingredient_reader = LuceneIndexReader(ingredient_path)
        self.content_reader = LuceneIndexReader(content_path)
        self.ingredient_searcher = LuceneSearcher(ingredient_path)
        self.content_searcher = LuceneSearcher(content_path)
        self.content_docinfo = []
        for i in range(self.content_searcher.num_docs):
            self.content_docinfo.append({
                'n': len(self.content_reader.analyze(self.content_searcher.doc(i).raw()['contents'])),
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