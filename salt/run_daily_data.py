import argparse
import daily_data
import datetime
import warnings

# Command Line Arguments
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--filename", help="Filename")
parser.add_argument("-a", "--automate", action='store_true') # Outputs a spreadsheet of unprocessed / dirty entries that can not be entered automatically
parser.add_argument("-m", "--manual", action='store_true') # Outputs a readable spreadsheet for data to be entered manually
parser.add_argument("-o", "--output", action='store_true')
parser.add_argument("-li", "--listitems", action='store_true', help="List Unique Items")

args = parser.parse_args()
if not args.filename:
       print("ERROR: Please add a file to read by typing '-f' before your filename")
       quit()

start_time = datetime.datetime.now()

dd = daily_data.DailyData(args.filename, args.automate, args.manual, args.output, args.listitems)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    dd.read_and_process_data()

end_time = datetime.datetime.now()
difference = end_time - start_time
diff_in_seconds = difference.total_seconds()
diff_in_minutes = divmod(diff_in_seconds, 60)[0]
print("Total Automation Time: " + str(diff_in_minutes) + " minutes")