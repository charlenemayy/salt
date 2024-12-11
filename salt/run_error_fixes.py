import argparse
import error_fixes
import warnings

# Command Line Arguments
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--filename", help="Filename")

args = parser.parse_args()
if not args.filename:
       print("ERROR: Please add a file to read by typing '-f' before your filename")
       quit()

ef = error_fixes.ErrorFixes(args.filename)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ef.read_and_process_data()
