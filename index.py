import os
import csv
java_home = os.environ.get('JAVA_HOME', None)
if not java_home:
    java_path = 'C:/Program Files/Java/jdk-21'
    os.environ['JAVA_HOME'] = java_path
else:
    print(java_home)

import json
from pyserini.analysis import Analyzer, get_lucene_analyzer
from pyserini.index import LuceneIndexReader
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

reader = LuceneIndexReader('indexes/content')
import itertools
for term in itertools.islice(reader.terms(), 10):
    print(f'{term.term} (df={term.df}, cf={term.cf})')

print(reader.stats())
