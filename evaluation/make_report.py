import json
import pandas as pd
from collections import defaultdict

INGREDIENTS_RAW_PATH = 'files/raw/foodrecipes_cleaned.json'

def format_block(key: str, body: list[dict]):
    res = f"\nQuery: {key}\nNarrative: (Same as before)\nAnnotated Results:\n"
    for i in range(len(body)):
        item = body[i]
        res += f"\t{i+1}. ({item['label']}) {item['title']} - {item['url']}\n"
    return res

with open(INGREDIENTS_RAW_PATH, 'r', encoding='utf-8') as f:
    recipes = json.load(f)
    recipe_dict = {x['canonical_url']:x['title'] for x in recipes}
    #print(recipe_dict)
df = pd.read_csv('evaluation\\UTF-8annotations_rrf.csv', dtype='string')
df = df.fillna("<blank>")
print(recipe_dict[df.head(10)['url'].iloc[0]])
url_col = df.columns.get_loc('url')
ingr_col = df.columns.get_loc('ingredients')
key_col = df.columns.get_loc('keywords')
label_col = df.columns.get_loc('label')
res = defaultdict(lambda :[])
for i in range(df.shape[0]):
    query = df.iloc[i, ingr_col] + " | " + df.iloc[i, key_col]
    res[query].append({
        'title': recipe_dict[df.iloc[i, url_col]],
        'label': df.iloc[i, label_col],
        'url': df.iloc[i, url_col]
    })
print(res[list(res.keys())[0]])
print(list(res.keys()))
with open('evaluation/report.txt', 'w', encoding='utf-8') as f:
    for key in res.keys():
        f.write(format_block(key, res[key]))