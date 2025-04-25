# Recipe Scraper

We introduce a recipe retrieval framework that supports composite queries comprising multiple ingredients and keyword terms (cuisine style, dietary tags). Our pipeline ingests raw recipe data from food.com, constructs inverted indices for both ingredient and keyword fields, and implements a weighted scoring function to balance ingredient preference and the keyword term preference.  The system is operationalized via a RESTful API that accommodates query formulations and filtering. Retrieval performance is evaluated using MAP@10 on both individual index components and their fused results. 

## Preparing Enviroment

There are several steps neeeded to make the retrieval work

### Install Requirements

Create a new Python enviroment and install requirements via `pip install -r requirements.txt`. Additionally, as the indexing requires Pyserini, make sure you have `Java 21` installed.

Lastly, because the processing of ingredients relies on `spacy` you need to download the model for processing. Run `spacy download en_core_web_sm`

### The Data and Indexing

The data was collected from [food.com](https://www.food.com/browse/allrecipes/) using the [recipe-scrapers](https://github.com/hhursev/recipe-scrapers) library and [scrapy](https://github.com/scrapy/scrapy) spider to control the throttling.

To make the retrieval work correctly make sure the files are located in the correct paths from the foot of the project

- All of the files are located in the google drive folder [here](https://drive.google.com/drive/u/0/folders/1MDrkxi8pz5gDx3J-t89UFLHiSmZY5imI) 
- You will see 3 files in there
  - `foodrecipes_scraped.zip` Unzip it inside the `files/raw` path. It is a zipped version of the raw scraped recipes.
  - `foodrecipes_cleaned.zip` Unqip it also in `files/raw`path. A cleaned version of the foodrecipes. It contains a preprocessed version of the ingredients that are going to be loaded directly into the index. The cleaning code is located in `scripts/clean_ingredients`
  - `synonyms.json` download it into `files/other`. This is a dictionary of synonyms with respective cosine similarity scores to each of the term, used during the retrieval. Was generated using `scripts/generate_synonyms.py`

As soon as the Data is downloaded you have to generate the indeces themselves. If you are on MAC or LINUX run `bash make_index.sh`, if on Windows `.\make_index.bat`. It will generate the Lucene index, with respective statistics and the recipe metadata storage. Be patient, it may take some time to process all of the recipes.

## Running the Retrieval

As soon as all of the indeces are working, we can run the retrieval. To accomplish that, you can run via command line

```bash
python search_script.py \
  --ingredients "chicken breast, garlic" \
  --keywords "quick" \
  --num-results 20 \
  --ranking rrf \
  --time-range 0 100 \
  --full \
  -o results.json
```
`--ingredients` and `--keywords` specify the query, `--full` specifies if we want to add all of the recipe information or not. There is also `--time-range` `--calories-range` and `--servings-range` that specify the filtering that is done after retrieval

## RESTful API

API is done via FastAPI, to run it install the library `pip install fastapi` and run `fastapi dev main.py`. you can go to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to see how the search works and which variables you can specify

## Evaluation

The queries that we were labeling are located in `evaluation/querries.csv`. We can generate the results via `evaluation/generate_results.py`

To label the results and see the label processing run the `evaluation/labeling.ipynb` file