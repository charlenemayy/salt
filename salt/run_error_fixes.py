import argparse
import error_fixes
import warnings

'''
will add file format guide to google drive!

ARGUMENTS (aug 2026)
location -l
project -p

location codes:
SEM (seminole), BIT (bithlo), YYA (youth), APO (apopka), KIS (kissimmee), ORL (orlando)

project codes (same as above, including):
HURRICANE_IAN, HURRICANE_HELENE_MILTON
'''

# Command Line Arguments
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--filename", help="Filename")
parser.add_argument("-p", "--project", help="Project")
parser.add_argument("-l", "--location", help="Location")

args = parser.parse_args()
if not args.filename:
       print("ERROR: Please add a file to read by typing '-f' before your filename")
       quit()

if not args.project:
       print("ERROR: Please add the project code (referenced in the code)")
       quit()

if not args.location:
       print("ERROR: Please add the location code (referenced in the code)")
       quit()

ef = error_fixes.ErrorFixes(args.filename)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ef.read_and_process_data(args.project, args.location)
