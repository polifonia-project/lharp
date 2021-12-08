"""
Utilities for the sonification of arbitrary symbolic sequences.
"""
import os
import time
import logging
import argparse

import note_seq
import numpy as np
import soundfile as sf

import joblib
from joblib import Parallel, delayed
from tqdm import tqdm

import ChordalPy

from constants import _DEFAULT_SAMPLE_RATE, SOUNDFONTS
from chord_lib import strip_chord_bass
from utils import is_file, create_dir

logger = logging.getLogger("hsimilarity.sonification")


def save_notesequence(note_sequence, out_dir, midi_fname=None, suffix=""):
  """
  Save the given note-sequence as a MIDI file in the desired directory.
  """
  if midi_fname is None:  # use a default naming convention
    date_and_time = time.strftime('%Y-%m-%d_%H%M%S')
    midi_fname = '%s_%s.mid' % (date_and_time, str(suffix))
  note_seq.sequence_proto_to_midi_file(
      note_sequence, os.path.join(out_dir, midi_fname))


def synthesise_sequence(
    note_sequence, out_file=None,
    synth=note_seq.midi_synth.synthesize,
    sample_rate=_DEFAULT_SAMPLE_RATE, **synth_args):
  """
  Sonification of a note-sequence object, through a synthetizer.
  Args:
    sequence: A music_pb2.NoteSequence to synthesize and play.
    out_file: filename of the audio file to be written.
    synth: A synthesis function that takes a sequence and sample rate as input.
    sample_rate: The sample rate at which to synthesize.
    **synth_args: Additional keyword arguments to pass to the synth function.
  """
  wave = synth(note_sequence, sample_rate=sample_rate, **synth_args)
  
  if out_file is not None:  # write the audio file to disk, if required
      sf.write(out_file, wave, sample_rate)

  return wave


def get_harmonic_notesequence(chord_annotations:list, fix_times=False, prog=0):
  """
  Create a note-sequence encoding the given harmonic progression.
  """
  if isinstance((chord_annotations[0]), (list, tuple)):
    chords = list(map(lambda x: x[0], chord_annotations))
    times = np.array(list(map(lambda x: x[1], chord_annotations)))
  else:  # in this case, timings of chords are not available
    chords = chord_annotations
    if not fix_times:  # inconsistent setup detected
      logger.warning(
        "Using fixed times for chords, as no timing information "
        "is available in the given harmonic annotations.")
      fix_times = True  # this is the only viable option
  # Append the end time of the latest chord, which is assumed to
  # have the same duration of the penultimate chord, or 1s frames.
  times = list(range(len(chords) + 1)) if fix_times else \
    np.append(times, [times[-1] + (times[-1] - times[-2])])

  chord_ns = note_seq.protobuf.music_pb2.NoteSequence()
  for i, chord_fig in enumerate(chords):  # iterate over all chords
      start_time, end_time = times[i], times[i+1]
      # Remove bass note before parsing the chord
      chord_nob = strip_chord_bass(chord_fig)
      # Append the major chord quality if absent
      if ":" not in chord_nob:
          chord_nob = chord_nob + ":maj"
      # Parse the chord and get the decomposition
      chord = ChordalPy.parse_chord(chord_nob)
      chord_pitches = [60 + offset for offset, idx 
          in enumerate(chord.get_note_array()) if idx != 0]
      
      for pitch in chord_pitches:  # add each note constituent
          chord_ns.notes.add(
              pitch=pitch, velocity=80, program=prog,
              start_time=start_time, end_time=end_time)

  chord_ns.total_time = chord_ns.notes[-1].end_time
  chord_ns.tempos.add(qpm=120)

  return chord_ns


def sonify_chord_sequence(
  track_name, chord_annotations, soundfont,
  out_dir="./", fix_times=False, prog=0):

  chord_ns = get_harmonic_notesequence(
    chord_annotations, fix_times=fix_times, prog=prog)

  save_notesequence(
    chord_ns, os.path.join(out_dir, "midi"), f"{track_name}.mid")
  synthesise_sequence(
    chord_ns, os.path.join(out_dir, "audio", f"{track_name}.wav"),
    synth=note_seq.midi_synth.fluidsynth, sf2_path=soundfont)
    

def main():
    """
    Main function to parse the arguments and call the main process.
    """

    parser = argparse.ArgumentParser(
        description='A simple sonification library for symbolic music.')
    
    parser.add_argument('data_bundle', type=lambda x: is_file(parser, x),
                        help='Path to the data bundle with symb sequences.')
    parser.add_argument('out_dir', action='store', type=str,
                        help='File system folder where audios will be saved.')
    
    # Embedding dataset- and model-related specifications
    parser.add_argument('--soundfont', choices=list(SOUNDFONTS.keys()),
                        help='The soundfont that the synthetiser will use.')
    parser.add_argument('--num_threads', action='store', type=int, default=1,
                        help='Number of threads to use for parallel execution.')
    parser.add_argument('--fix_times', action='store_true', default=False,
                        help='Whether the durations should be discarded.')
    parser.add_argument('--program', action='store', type=int, default=0,
                        help='Program MIDI number of the instrument to use.')
    
    # Logging and checkpointing 
    parser.add_argument('--log_dir', action='store',
                        help='Directory where log files will be generated.')
    parser.add_argument('--resume', action='store_true', default=False,
                        help='Whether to resume the sonification process.')    


    args = parser.parse_args()

    with open(args.data_bundle, "rb") as fo:
        data = joblib.load(fo)
    data = data["preproc"]  # FIXME!

    out_dir = create_dir(args.out_dir)  # create the root output dir
    create_dir(os.path.join(args.out_dir, "midi"))
    create_dir(os.path.join(args.out_dir, "audio"))
    soundfont = SOUNDFONTS[args.soundfont]

    print("Found {} chord sequences to sonify".format(len(data)))
    print(f"Running sonification using {args.num_threads} threads. Be patient.")
    Parallel(n_jobs=args.num_threads)(delayed(sonify_chord_sequence)\
      (track_name, chord_annotations, soundfont,
       out_dir, args.fix_times, args.program) \
         for track_name, chord_annotations in tqdm(data.items()))
    
    print('Done!')

if __name__ == "__main__":
    main()