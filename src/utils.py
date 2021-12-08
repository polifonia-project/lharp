import os
from itertools import groupby
from datetime import timedelta


def is_file(parser, f_arg):
      if not os.path.exists(f_arg):
          return parser.error("File %s does not exist!" % f_arg)
      return f_arg  # returned only if the file exists


def create_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path


def flatten_list(t:list):
    return [item for sublist in t for item in sublist]


def remove_consecutive_repeats(t):
    return [x[0] for x in groupby(t)]


def convert_time(t):
    return str(timedelta(seconds=t))
