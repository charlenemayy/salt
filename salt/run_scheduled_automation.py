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
    export_name = "Apopka" #TODO: eventually change to 'all_locations'
    location_name = "All SALT Locations"
    location_key = "ALLSALT"

    # make output text file for log of daily run
    log_filename = location_key + "_RUNLOG_" + date_str + ".txt"
    log_report_path = output_path + log_filename

    with open(log_report_path, 'a') as f:
        f.write("RUN LOGS OF CONSOLE OUTPUT FOR " + date_str)
        f.write("\n********************************************************************\n\n")

    if not args.skipfirstrun:
        filename_date = date_str[6:10] + "-" + date_str[0:5]
        report_filename = "client_summary_log_" + export_name + "_" + filename_date + "_to_" + filename_date + ".csv"
        report_path = output_path + report_filename

        if not os.path.exists(report_path):
            print("ERROR: Downloaded report for " + location_name + " cannot be found")
            with open(log_report_path, 'a') as f:
                f.write("ERROR: Downloaded report for " + location_name + " cannot be found")
            return

        # download pretty xlsx file to upload to drive
        print("RUNNING: Processing simplified report file")
        with open(log_report_path, 'a') as f:
            f.write("RUNNING: Processing simplified report file")
            f.write("\n********************************************************************\n\n")
        subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -f {0} -m >> {1}".format(report_path, log_report_path)], shell=True)

        # start first run of automation
        print(f"RUNNING: Starting first run of automation for {location_name}")
        with open(log_report_path, 'a') as f:
            f.write(f"RUNNING: Starting first run of automation for {location_name}")
            f.write("\n********************************************************************\n\n")
        subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -f {0} -a >> {1}".format(report_path, log_report_path)], shell=True)

    # run the failed entries
    failed_report_filename = location_key + "_Failed_entries_" + date_str + ".xlsx"
    failed_report_path = output_path + failed_report_filename

    for i in range(run_count):
        if not os.path.exists(failed_report_path):
            print(f"ERROR: Failed entry report for {location_name} from SALT cannot be found")
            with open(log_report_path, 'a') as f:
                f.write(f"ERROR: Failed entry report for {location_name} from SALT cannot be found")
        else:
            print(f"\nRUNNING: Automating failed {location_name} entries -- Run #{i+1}")
            with open(log_report_path, 'a') as f:
                f.write(f"\nRUNNING: Automating failed {location_name} entries -- Run #{i+1}")
                f.write("\n********************************************************************\n\n")

            subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -f {0} -a >> {1}".format(failed_report_path, log_report_path)], shell=True)

            # upload final instance of the failed entry report to drive
            gauth = GoogleAuth() 
            drive = GoogleDrive(gauth)

    # upload failed report path to google drive
    gfile = drive.CreateFile({'parents': [{'id': '15sT6EeVyeUsMd_vinRYgSpncosPW7B2s'}], 'title': failed_report_filename}) 
    gfile.SetContentFile(failed_report_path)
    gfile.Upload()

    print(f"SUCCESS: Finished running {location_name} entries!\n")
    with open(log_report_path, 'a') as f:
        f.write(f"SUCCESS: Finished running {location_name} entries!\n")
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
parser.add_argument("-sfr", "--skipfirstrun", action="store_true")

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