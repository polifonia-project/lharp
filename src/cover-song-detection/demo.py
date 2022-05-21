import csv
from difflib import SequenceMatcher
from itertools import groupby, combinations

import joblib
import statistics
import pandas as pd

from src.harmonic_lib import ngram_hsim
from src.ngrams_lib import extract_ngrams

## Create numerical values out of vectors
vector_chords = joblib.load('../data/converted_simplified.joblib')

chord_encoded = {}
for track_name, chords in vector_chords.items():
    chord_encoded[track_name] = []
    chord_list = []
    for chord in chords:  # iterating over chords\n",
        extended_chord = chord[1]#  + [chord[0]]
        token = ''.join([str(x) for x in extended_chord[:3]])
        chord_list.append(int(token))
    chord_encoded[track_name] = chord_list
# print(chord_encoded)

## Remove consecutive duplicates
chord_encoded_cleaned = {}
for track, encoded_chords in chord_encoded.items():
    chord_encoded_cleaned[track.replace('.jams', '')] = [key for key, _group in groupby(encoded_chords)]
    # print(chord_encoded_cleaned)

## Calculate n-grams
recurring_patterns = {}
for track_name, chords in chord_encoded_cleaned.items():
    recurring_patterns.update(extract_ngrams(track_name, chords, n_start=3))
    # print(recurring_patterns)
joblib.dump(recurring_patterns, 'ngrams_type.joblib')

# Calculate similarity
hsim_map_mini = {track_id: {} for track_id in list(recurring_patterns.keys())}

# calculate hsim
for x, y in combinations(recurring_patterns.keys(), 2):
    if len(recurring_patterns[x]) > 0 and len(recurring_patterns[y]) > 0:
        hsim, longest_rps = ngram_hsim(recurring_patterns[x], recurring_patterns[y])
        if hsim > 0.:  # save only non-trivial
            hsim_map_mini[x][y] = hsim, longest_rps
joblib.dump(hsim_map_mini, 'hsim_type.joblib')


hsim_map_mini = joblib.load('hsim_type.joblib')
# get names
with open('../data/biab_metadata.csv', 'r') as csv_file:
    meta_obj = csv.reader(csv_file)
    next(meta_obj)
    meta = {}
    for filename, title in meta_obj:
        meta[filename.replace('.jams', '')] = title

similarities, covers = [], []
for k, v in hsim_map_mini.items():
    for similar, similar_value in v.items():
        this_similarity = [meta[k], meta[similar], similar_value[0]]
        if SequenceMatcher(None, meta[k], meta[similar]).ratio() >= .8:
            this_similarity.append(True)
            covers.append([meta[k], meta[similar], similar_value[0]])
        else:
            this_similarity.append(False)
        similarities.append(this_similarity)

hsim_df = pd.DataFrame(similarities, columns=['track_1', 'track_2', 'similarity_value', 'cover'])
hsim_df.sort_values(by=['similarity_value'], inplace=True, ascending=True)
hsim_df.to_csv('similarities_type.csv', index=False)

# parse ALL metadata (SLOW)
# with open('../data/biab_metadata.csv', 'r') as csv_file:
#     meta_obj = csv.reader(csv_file)
#     next(meta_obj)
#     tracklist = [y for x, y in meta_obj]
#
# all_covers = [(t1, t2) for t1, t2 in combinations(tracklist, 2) if SequenceMatcher(None, t1, t2).ratio() > .8]
# print(len(all_covers))

with open('similarities_type.csv', 'r') as csv_file:
    meta_obj = csv.reader(csv_file)
    next(meta_obj)

    all_similarities = [float(x[2]) for x in meta_obj ]
    print(len(all_similarities))
    print('avg sim', statistics.fmean(all_similarities))

