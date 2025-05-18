from datetime import date
from datetime import timedelta
from datetime import datetime
import os
import platform
import subprocess
import json
import time
import argparse
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

'''
Automates the entire daily data process, from downloading the report in the SALT Web app to 
inputting into HMIS, including running the failed entries several times. This is meant to be 
run late at night, every night. 

This was developed based on my personal environment in MacOS and will not work in other operating systems.
'''

def run_daily_data(location_key, location_name, location_version):
    # for the old web app, we can automate the download of the day's report from the website
    if location_version == 'oldapp':
        files = os.listdir(output_path)
        report_filename = "Report_by_client_" + date_str + ".xlsx"

        # delete any existing reports
        if report_filename in files:
            subprocess.run(["rm {0}".format(report_filename)], shell=True)

        # download yesterday's report
        print(f"RUNNING: Downloading {location_name} report from the SALT Web App")
        subprocess.run(["/usr/bin/python3 salt/run_daily_report.py -l \"{0}\" -d {1}".format(location_key, date_str)], shell=True)
        time.sleep(5)

        # double check that report has been downloaded / exists
        report_path = output_path + report_filename
        if not os.path.exists(report_path):
            print("ERROR: Downloaded report from SALT cannot be found")
            return
    # for the new web app, we have to manually download the exports locally before we can run our scheduled automation (for now)
    elif location_version == 'newapp':
        report_filename = location_key + "-Export-" + date_str + ".xlsx"

        # double check that report has been downloaded / exists
        report_path = output_path + report_filename
        if not os.path.exists(report_path):
            print("ERROR: Downloaded report for " + location_name + " cannot be found")
            return
    
    # download pretty xlsx file to upload to drive
    print("RUNNING: Processing simplified report file")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l {0} -f {1} -m".format(location_key, report_path)], shell=True)

    # start first run of automation -- if its the newer app, skip the first row as 
    # this usually contains the date and messes with the export intake
    print(f"RUNNING: Starting first run of automation for {location_name}")
    if location_version == 'oldapp':
        subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l {0} -f {1} -a".format(location_key, report_path)], shell=True)
    elif location_version == 'newapp':
        subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l {0} -f {1} -a --skipfirstrow".format(location_key, report_path)], shell=True)

    # run the failed entries
    failed_report_filename = location_key + "_Failed_entries_" + date_str + ".xlsx"
    failed_report_path = output_path + failed_report_filename

    if not os.path.exists(failed_report_path):
        print(f"Failed entry report for {location_name} from SALT cannot be found, continuing data entry")
    else:
        print(f"\nRUNNING: Automating failed {location_name} entries")
        subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l {0} -f {1} -a".format(location_key, failed_report_path)], shell=True)

        # upload final instance of the failed entry report to drive
        gauth = GoogleAuth() 
        drive = GoogleDrive(gauth)

        gfile = drive.CreateFile({'parents': [{'id': '15sT6EeVyeUsMd_vinRYgSpncosPW7B2s'}], 'title': failed_report_filename}) 
        gfile.SetContentFile(failed_report_path)
        gfile.Upload()

    # delete report file from sanford location
    subprocess.run(["rm {0}".format(report_path)], shell=True)

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
parser.add_argument("-sor", "--skiporlando", action="store_true")
parser.add_argument("-ssf", "--skipsanford", action="store_true")
parser.add_argument("-sbl", "--skipbithlo", action="store_true")
parser.add_argument("-syo", "--skipyouth", action="store_true")

args = parser.parse_args()

if args.date:
    date_str = args.date
else:
    # get yesterday's date
    yesterday = date.today() - timedelta(days=1)
    date_str = datetime.fromordinal(yesterday.toordinal()).strftime("%m-%d-%Y")

# locations to automate on this run
locations = [
    {
        'key': "ORL",
        'name': "ORLANDO",
        'skip': args.skiporlando,
        'version': 'newapp'
    },
    {
        'key': "SEM",
        'name': "SANFORD",
        'skip': args.skipsanford,
        'version': 'oldapp'
    },
    {
        'key': "BIT",
        'name': "BITHLO",
        'skip': args.skipbithlo,
        'version': 'oldapp'
    },
    {
        'key': "YYA",
        'name': "YOUTH",
        'skip': args.skipyouth,
        'version': 'newapp'
    }
]

for location in locations:
    print(location)
    if not location['skip']:
        run_daily_data(location['key'], location['name'], location['version'])

print("SUCCESS: Finished running scheduled automation!")
# lock mac when done
if not args.leaveunlocked:
    os.system("pmset displaysleepnow")