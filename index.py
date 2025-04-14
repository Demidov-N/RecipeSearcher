import os
import csv

import json

from pyserini.analysis import Analyzer, get_lucene_analyzer
from pyserini.index import LuceneIndexReader

# SETTINGS
INGREDIENTS_RAW_PATH = 'files/raw/foodrecipes.json'
INGREDIENT_INDEX_PATH = 'files/index_jsons/ingredients/ingredients.json'
CONTENT_INDEX_PATH = 'files/index_jsons/content/content.json'

analyzer = Analyzer(get_lucene_analyzer())

def filter_csv(filename):
    output_rows = []
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=",")
        for row in reader:
            if(row[5] != 'Gathered' or 'food.com' not in row[4]):
                continue
            output_rows.append(row)
    with open('trimmed_dataset.csv', 'w', encoding='utf-8', newline='') as output:
        writer = csv.writer(output)
        output.write(',title,ingredients,directions,link,source,NER\n')
        for row in output_rows:
            writer.writerow(row)

#filter_csv('full_dataset.csv')
def build_indices():
    with open('trimmed_dataset.csv', newline='', encoding='utf-8') as f:
        index_source = []
        index_ingredients = []
        index_content = []
        csv_reader = csv.DictReader(f, delimiter=",")
        for row in csv_reader:
            content = row['title'] + '\n' + '\n'.join(json.loads(row['directions']))
            ingredients = json.loads(row['NER'])
            index_source.append({
                'id': row['link'],
                'content': content,
                'content_length': len(analyzer.analyze(content)),
                'ingredients': ingredients,
            })
            index_ingredients.append({
                'id': row['link'],
                'contents': ', '.join(ingredients)
            })
            index_content.append({
                'id': row['link'],
                'contents': content
            })
        with open('ingredients/ingredients.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(index_ingredients))
        with open('content/content.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(index_content))

def build_indices_from_json():
    os.makedirs(os.path.dirname(INGREDIENT_INDEX_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(CONTENT_INDEX_PATH), exist_ok=True)
    with open(INGREDIENTS_RAW_PATH, encoding='utf-8') as f:
        recipes = json.load(f)
        index_ingredients = []
        index_content = []
        for i in range(250000):
            if i >= len(recipes):
                break
            recipe = recipes[i]
            index_ingredients.append({
                'id': recipe['canonical_url'],
                'contents': ', '.join(recipe['ingredients'])
            })
            keywords = ' '.join(recipe['keywords']) if 'keywords' in recipe.keys() else " "
            yields =  recipe['yields'] if 'yields' in recipe.keys() else " "
            description = recipe['description'] if 'description' in recipe.keys() else " "
            index_content.append({
                'id': recipe['canonical_url'],
                'contents': '\n'.join([recipe['title'], description, keywords, yields])
            })
        with open(INGREDIENT_INDEX_PATH, 'w+', encoding='utf-8') as file:
            file.write(json.dumps(index_ingredients))
        with open(CONTENT_INDEX_PATH, 'w+', encoding='utf-8') as file:
            file.write(json.dumps(index_content))


build_indices_from_json()

#use this code to see index stats
#reader = LuceneIndexReader('indexes/content')
#import itertools
#for term in itertools.islice(reader.terms(), 5):
#    print(f'{term.term} (df={term.df}, cf={term.cf})')

#print(reader.stats())
#print(reader.doc("https://www.food.com/recipe/1-pot-4-item-sausage-suprise-447710").raw())
