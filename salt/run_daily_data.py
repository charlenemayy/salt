import argparse
import pandas as pd
import daily_data

# Command Line Arguments
parser = argparse.ArgumentParser()
parser.add_argument("-l", "--listitems", action='store_true', help="List Unique Items")
parser.add_argument("-f", "--filename", help="Filename")
parser.add_argument("-o", "--output", action='store_true')
parser.add_argument("-a", "--automate", action='store_true') # Outputs a spreadsheet of unprocessed / dirty entries that could not be entered automatically
parser.add_argument("-m", "--manual", action='store_true') # Outputs a readable spreadsheet for data to be entered manually

args = parser.parse_args()

df = pd.read_excel(io=args.filename,
                     dtype={'': object,
                            'DoB': object,
                            'Client Name': object,
                            'HMIS ID': object,
                            'Race': object,
                            'Ethnicity': object,
                            'Verification of homeless': object,
                            'Gross monthly income': object,
                            'Service': object,
                            'Items': object})

dd = daily_data.DailyData(df, args.filename, args.automate, args.manual, args.output, args.listitems)
dd.read_and_process_data()
if args.manual:
       dd.export_manual_entry_data("~/Desktop/SALT/output/")
if args.automate:
       dd.export_failed_automation_data("~/Desktop/SALT/output/")