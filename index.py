import os
import csv
java_home = os.environ.get('JAVA_HOME', None)
if not java_home:
    java_path = 'C:/Program Files/Java/jdk-21'
    os.environ['JAVA_HOME'] = java_path
else:
    print(java_home)

from pyserini.index import LuceneIndexReader

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
with open('trimmed_dataset.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=",")
    for row in reader:
        print(row)
        break