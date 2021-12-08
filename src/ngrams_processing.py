from ngrams_lib import *
from utils import convert_time
import random
import json

HSIM_ENCODING_BUNDLE = '../setup/sonar_hsim_map_global.joblib'


def open_encoded(encoded_path):
    with open(encoded_path, "rb") as eb:
        enc = joblib.load(eb)
        return enc['encoded']


def open_hsim_map(hsim_map_path):
    with open(hsim_map_path, "rb") as cd:
        data = joblib.load(cd)
        return data


def align_data(hsim_map, encoded_chord, track_title):
    all_all = []
    for tr_name in hsim_map['hsim_map']:
        maps = hsim_map['hsim_map'][tr_name]
        for m in maps:
            file_id_a = ids.index(tr_name)
            file_id_b = ids.index(m)
            id1 = track_title[file_id_a]
            if type(id1) != float:
                id_a = ''.join([i for i in id1 if not i.isdigit()]).replace('-', '').replace('_', '').replace('CD', '') \
                    .replace('BackInTheU.S.S.R.', 'BackInTheUSSR')
                # if id_a in spoty_names:
                #     point_a = spoty_names.index(id_a)
                #     s_id_a = spoty_uri[point_a]
                # else:
                #     s_id_a = None
            id2 = track_title[file_id_b]
            if type(id2) != float:
                id_b = ''.join([i for i in id2 if not i.isdigit()]).replace('-', '').replace('_', '').replace('CD', '') \
                    .replace('BackInTheU.S.S.R.', 'BackInTheUSSR')
                # if id_b in spoty_names:
                #     point_b = spoty_names.index(id_b)
                #     s_id_b = spoty_uri[point_b]
                # else:
                #     s_id_b = None

            # print(id_b)
            # spotify_link_a = get_spotify_link(path_a)

            sim_val, patterns = maps[m]
            tr_raw_a = raw[tr_name]
            tr_raw_b = raw[m]
            encoded_ch_a = encoded_chord[tr_name]
            encoded_ch_b = encoded_chord[m]
            chords_a = [c for c, t in tr_raw_a]
            chords_b = [c for c, t in tr_raw_b]
            timestamps_a = [t for c, t in tr_raw_a]
            timestamps_b = [t for c, t in tr_raw_b]
            patterns_index_a = [single_ngram_position(encoded_ch_a, pattern) for pattern in patterns]
            patterns_index_b = [single_ngram_position(encoded_ch_b, pattern) for pattern in patterns]
            pattern_raw_a = [chords_a[i:i + l] for i, l in patterns_index_a]
            pattern_raw_b = [chords_b[i:i + l] for i, l in patterns_index_b]
            pattern_time_a = [(convert_time(timestamps_a[i]), convert_time(timestamps_a[i + l])) for i, l in
                              patterns_index_a]
            pattern_time_b = [(convert_time(timestamps_b[i]), convert_time(timestamps_b[i + l])) for i, l in
                              patterns_index_b]
            pattern_times_a = [(timestamps_a[i: i + l + 1]) for i, l in
                               patterns_index_a]
            pattern_times_b = [(timestamps_b[i: i + l + 1]) for i, l in
                               patterns_index_b]

            sc_link_a = [f"https://soundcloud.com/jacopo-de-berardinis/{tr_name.replace('_', '-')}#t={timestamps_a[i]}"
                         for i, l in patterns_index_a]
            sc_link_b = [f"https://soundcloud.com/jacopo-de-berardinis/{m.replace('_', '-')}#t={timestamps_b[i]}"
                         for i, l in patterns_index_b]

            cp_matches = []
            for i, num in enumerate(range(len(pattern_raw_a))):
                all = [tr_name,
                       m,
                       pattern_raw_a[num],
                       pattern_raw_b[num],
                       pattern_time_a[num],
                       pattern_time_b[num],
                       ''.join(str(_) for _ in sc_link_a[num]),
                       ''.join(str(_) for _ in sc_link_b[num]),
                       # s_id_a,
                       # s_id_b,
                       None,
                       None]

                cp_match = {"cpMatchId": f"{i + 1:05d}",
                            "humanSimScore": None,
                            'cpaA': {
                                "id": tr_name + '_' + '_'.join(pattern_raw_a[num]),
                                "start": pattern_time_a[0][0],
                                "end": pattern_time_a[0][1],
                            },
                            'cpaB': {
                                "id": m + '_' + '_'.join(pattern_raw_b[num]),
                                "start": pattern_time_b[0][0],
                                "end": pattern_time_b[0][1],
                            }
                            }
                cp_matches.append(cp_match)

            all_dict = {'recordingA': tr_name,
                        'recordingB': m,
                        'compSimScore': sim_val,
                        }
            all_dict.update({'cpMatches': cp_matches})

            all_times = [tr_name, m, sim_val, pattern_raw_a, pattern_raw_b, pattern_times_a, pattern_times_b]
            all_all.append(all_dict)

    with open("../harmonic_similarity.json", "w") as outfile:
        json.dump({'harSimPairs': all_all}, outfile, indent=4)

    return all_all


def create_spreadsheets(data_list):
    z = 0
    while z < 1000:
        choice_list = []
        temp_choice = []
        z += 1
        while len(choice_list) < 15:
            choice = random.choice(data_list)
            index_a = ids.index(choice[0])
            index_b = ids.index(choice[1])
            if f"{choice[0]}+{choice[1]}" not in temp_choice and artist[index_a] != artist[index_b] and title[index_a] \
                    != title[index_b]:
                choice_list.append(choice)
                temp_choice.append(f"{choice[1]}+{choice[0]}")
                choice_index = data_list.index(choice)
                data_list.pop(choice_index)
            else:
                continue

            df = pd.DataFrame(choice_list, columns=['track_1',
                                                    'track_2',
                                                    'pattern_track_1',
                                                    'pattern_track_2',
                                                    'time_pattern_track_1',
                                                    'time_pattern_track_2',
                                                    'sonification_pattern_track_1',
                                                    'sonification_pattern_track_2',
                                                    'spotify_uri_track_1',
                                                    'spotify_uri_track_2',
                                                    'Is the shared pattern good for the demo? (Yes/No)',
                                                    'Rate the goodness of the shared pattern (from 1 to 5)'])

            df.to_excel(f'split_global/harmonic_similarity_timestamps_{z}.xlsx', index=False)


if __name__ == '__main__':

    raw = open_chord(CHORDS_PATH)
    ids, title, artist, paths = open_meta(DATASET_META)
    encoding = open_encoded(ENCODED_PATH)
    hsim_encoding = open_hsim_map(HSIM_ENCODING_BUNDLE)
    encoded = open_encoded(ENCODED_PATH)

    align_data(hsim_encoding, encoded, title)

