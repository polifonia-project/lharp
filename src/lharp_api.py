'''
A collection of simplified functions to compute the LRP harmonic similarity.
'''

from ChordalPy.Transposers import transpose

from ngrams_lib import extract_ngrams
from harmonic_lib import ngram_hsim
from chord_encodings import ChordEncodingError


CHORD_MAP = {
    "E:min7(b5)": "E:min7",
    "F:min7(b5)": "F:min7"
}


def preprocess_chord_sequences(chord_json:str):
    """
    Pre-process a simple JSON file containing a chord annotation for each
    track (a simple annotation is an ordered list of chords together with
    key information). This is needed to avoid encoding issues.

    Args:
        - chord_json (str): path to a JSON file with chord annotations.
    
    Returns:
        - a dictionary with the pre-processed annotations, indexed by
            the name/id of each track (the same used in the given JSON).
        - another dictionary containing only key information per track.
    
    Notes:
        - Add the other pre-processing steps (e.g. remove cons. repeats).
        - I would replace the CHORD_MAP with a simple utility that tries
            to remove the alterations if a chord symbol cannot be parsed,
            throwing a warning in that case; failing instead if the symbol
            cannot still be parsed after the correction attempt.
    """
    chord_pproc = {}
    key_dict = {}

    for track_name, track_ann in chord_json.items():
        key_dict[track_name] = track_ann["key"]
        chord_pproc[track_name] = []
        # Pre-process one after the other
        for chord in track_ann["chord"]:
            chord_class = chord[0]  # just keep the label
            chord_class = CHORD_MAP.get(chord_class, chord_class)
            chord_pproc[track_name].append(chord_class)

    return chord_pproc, key_dict


def normalise_chord_sequences(chord_dict:dict, key_dict:dict):
    """
    Normalise each chord annotation by transposing the harmonic
    progression to the target global key (tonic and scale).

    Args:
        chord_dict (dict): a dictionary holding the pre-processed
            chord sequences, where each element is indexed by track id.
        key_dict (dict): key annotations for each track (same IDs).

    Returns: a dictionary with all chord annotatioons transposed
        to the same key (Cmaj).

    Notes:
        - At the moment, we ignore the scale for the transposition and
            only consider the tonic (this should be improved).
        - By default, this transposes everything to Cmaj, although we
            may want to parameterise this in the function.

    """
    assert set(chord_dict.keys()) == set(key_dict.keys()), \
        "The given chord and key annotations are not aligned by ID."
    chord_transp = {}  # the dictionary simply holds the transpositions

    for track_name in chord_dict.keys():
        track_gkey = key_dict[track_name][0]
        track_gkey = track_gkey[0].split(":")[0]
        # Ready to transpose -- only at the tonic-level
        transposed = []  # holds the transpositions
        for chord in chord_dict[track_name]:
            transposed.append(transpose(chord, track_gkey))
        # Update the transp-specific dict
        chord_transp[track_name] = transposed

    return chord_transp


def encode_chord_sequences(chord_norm:dict, encdec):
    """
    Encode sequences of chord symbols/labels expressed in Harte notation,
    using the given encoder-decoder instance (arbitrary chord encodings
    are thus supported). If an illegal chord label is found (one that
    cannot be encoded) an error is thrown and a message is printed.

    Args:
        - chord_norm (dict): pre-processed and normalised chord sequences,
            indexed by track id in the dictionary.
        - encdec (EncoderDecoder): an instance of an encoder-decoder that
            transforms a chord label into an integer number (one-hot).

    Returns: a dictionary with the encoded chord sequences.

    Notes
        - This should simply throw an exception rather than printing.
    """
    chord_encoded = {}

    for track_name, chords in chord_norm.items():
        chord_encoded[track_name] = []
        for chord in chords:  # iterating over chords
            try:  # attempting encoding, if possible
                hash = encdec._compute_chord_hash(chord)
                token = encdec.hash_to_index[hash]
                chord_encoded[track_name].append(token)
            except:  # this should abort the whole process
                print(f"Could not encode: {chord}")
                raise ChordEncodingError(chord)
    
    return chord_encoded


def extract_recurring_pattern(chord_enc:dict, min_order=3):
    """
    Extract a bag of recurring patttern from each normalised chord annotation,
    excluding patterns of lower order.

    Args:
        chord_enc (dict): encoded chord sequences indexed by track id.
        min_order (int): the minimum length of full repetitions to extract.

    Returns: a dictionary with all the recurring patterns for each track.
    """
    assert min_order > 1, "Order needs to be strictly greater than 1."
    recurring_patterns = {}  # per-track bag of recurring patterns

    for track_name, chords in chord_enc.items():
        recurring_patterns.update(extract_ngrams(
            track_name, chords, n_start=3))

    return recurring_patterns


def dictionarify_recpat_data(recpat_data):
    """
    Covert a list of flat dictionaries (single-record dicts) into a dictionary.
    If the given data structure is already a dictionary, it is left unchanged.
    """

    return {track_id[0]: patterns[0] for track_id, patterns in \
            [zip(*item.items()) for item in recpat_data]} \
                if not isinstance(recpat_data, dict) else recpat_data


def harmonic_similarity_inter(
    chords_recpat_in:dict, chords_recpat_target:dict, encdec, duplicate=False):
    """
    Compute the harmonic similarity of a new group of tracks with pieces that
    have already been processed (e.g. in previous study).

    Args:
        - chords_recpat_in (dict): the reccuring patterns extracted for each
            chord annotation (a list of tuple for each entry) in the new group.
        - chords_recpat_target (dict): same as before, but for the target group.
        - encdec (EncoderDecoder): the encoder-decoder that will be used to
            convert the longest shared recurring patterns in the output map.
        - duplicate (bool): whether the harmonic similarity map to return is
            made symmetric -- entries are replicated (A[i,j] == A[j,i]). 
    
    Returns: the hsim_map, a matrix encoding the pair-wise harmonic similarity
        among tracks in `chords_recpat_in` and those in `chords_recpat_target`.
        This is done for computational concerns, as the main hsim_map encoding
        the pair-wise similarities within the latter may already be available.
        The matrix also includes the longest shared recurring pattern on which
        the harmonic similarity is based (useful for interpretation).

    Notes:
        - Include a parameter for making the dictionary simmetric, meaning
            that entries are replicated (A[i,j] == A[j,i]). 
    """
    hsim_map = {id: {} for id in list(chords_recpat_in.keys())}

    for track_name, track_brps in chords_recpat_in.items():
        for target_name, target_brps in chords_recpat_target.items():
            # Compute the harmonic similarity between the pair
            hsim, longest_rps = ngram_hsim(track_brps, target_brps)
            longest_rps = [[encdec.decode_event(idx) for idx in lsrp_shot] \
                for lsrp_shot in longest_rps]  # keep and decode
            if hsim > 0.:  # save only non-trivial similarities
                hsim_map[track_name][target_name] = hsim, longest_rps
                if duplicate:  # replicate the hsim info if needed
                    hsim_map[target_name][track_name] = hsim, longest_rps

    return hsim_map


def harmonic_similarity_intra(chords_recpat:dict, encdec, duplicate=True):
    """
    Compute the pair-wise harmonic similarity between tracks, for which their
    recurring patterns are provided. The similarity value, together with the
    longest shared recurring patterns, are returned in dictionary matrix --
    the harmonic similarity map. Please note that this last data structure only
    include strictly positive similarities to avoid sparsity and memory issues.

    Args:
        - chords_recpat (dict): the reccuring patterns extracted for each
            chord annotation (a list of tuple for each entry) in the new group.
        - encdec (EncoderDecoder): the encoder-decoder that will be used to
            convert the longest shared recurring patterns in the output map.
        - duplicate (bool): whether the harmonic similarity map to return is
            made symmetric -- entries are replicated (A[i,j] == A[j,i]).

    Returns: the hsim_map, a matrix encoding the pair-wise harmonic similarity
        among tracks in `chords_recpat`, including the longest shared recurring
        pattern on which the similarity is based (useful for interpretation).
    """
    track_ids = list(chords_recpat.keys())
    hsim_map = {track_id: {} for track_id in track_ids}

    for i, track_a in enumerate(track_ids):
        a_rpbag = chords_recpat[track_a]
        for j in range(i+1, len(track_ids)):
            track_b = track_ids[j]
            b_rpbag = chords_recpat[track_b]
            # Compute the harmonic similarity and update map
            hsim, longest_rps = ngram_hsim(a_rpbag, b_rpbag)
            longest_rps = [[encdec.decode_event(idx) for idx in lsrp_shot] \
                for lsrp_shot in longest_rps]  # keep and decode patterns
            if hsim > 0.:  # populate the matrix only non-trivial
                hsim_map[track_a][track_b] = hsim, longest_rps
                if duplicate:  # replicate the hsim info if needed
                    hsim_map[track_b][track_a] = hsim, longest_rps

    return hsim_map

