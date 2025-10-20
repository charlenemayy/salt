from datetime import date
from datetime import timedelta
from datetime import datetime
import os
import subprocess
import json
import argparse
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

'''
Automates the entire daily data process, from downloading the report in the SALT Web app to 
inputting into HMIS, including running the failed entries several times. This is meant to be 
run late at night, every night. 

This was developed based on my personal environment in MacOS and will not work in other operating systems.
'''

def run_daily_data():
    files = os.listdir(output_path)
    export_name = "Apopka" #TODO: eventually change to 'all_locations'
    location_name = "All SALT Locations"
    location_key = "ALLSALT"

    filename_date = date_str[6:10] + "-" + date_str[0:5]
    report_filename = "client_summary_log_" + export_name + "_" + filename_date + "_to_" + filename_date + ".csv"

    report_path = output_path + report_filename
    if not os.path.exists(report_path):
        print("ERROR: Downloaded report for " + location_name + " cannot be found")
        return

    # download pretty xlsx file to upload to drive
    print("RUNNING: Processing simplified report file")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -f {0} -m".format(report_path)], shell=True)

    # start first run of automation
    print(f"RUNNING: Starting first run of automation for {location_name}")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -f {0} -a".format(report_path)], shell=True)

    # run the failed entries
    failed_report_filename = location_key + "_Failed_entries_" + date_str + ".xlsx"
    failed_report_path = output_path + failed_report_filename

    if not os.path.exists(failed_report_path):
        print(f"Failed entry report for {location_name} from SALT cannot be found")
    else:
        print(f"\nRUNNING: Automating failed {location_name} entries")
        subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l {0} -f {1} -a".format(location_key, failed_report_path)], shell=True)

        # upload final instance of the failed entry report to drive
        gauth = GoogleAuth() 
        drive = GoogleDrive(gauth)

        gfile = drive.CreateFile({'parents': [{'id': '15sT6EeVyeUsMd_vinRYgSpncosPW7B2s'}], 'title': failed_report_filename}) 
        gfile.SetContentFile(failed_report_path)
        gfile.Upload()

    print(f"SUCCESS: Finished running {location_name} entries!\n")
    return

'''
 ######## MAIN SCRIPT ########
'''

# SETTINGS
run_count = 3 # amount of times to run the failed entry automation

# grab output path from settings.json
try:
    filename = "./salt/settings.json"
    f = open(filename)
    data = json.load(f)
except Exception as e:
    print("ERROR: 'settings.json' file cannot be found, please see README for details")
    quit()
settings = data["data"][0]
output_path = settings["output_path"]

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--date")
parser.add_argument("-lu", "--leaveunlocked", action="store_true")

args = parser.parse_args()

if args.date:
    date_str = args.date
else:
    # get yesterday's date
    yesterday = date.today() - timedelta(days=1)
    date_str = datetime.fromordinal(yesterday.toordinal()).strftime("%m-%d-%Y")

run_daily_data()

print("SUCCESS: Finished running scheduled automation!")
# lock mac when done
if not args.leaveunlocked:
    os.system("pmset displaysleepnow")