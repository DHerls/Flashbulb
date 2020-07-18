import argparse

from _tools.stage_function import stage_function

parser = argparse.ArgumentParser()
parser.add_argument('function_key')
config = parser.parse_args()

stage_function(config.function_key)
