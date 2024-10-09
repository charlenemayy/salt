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
parser.add_argument("-sfr", "--skipfirstrun", action="store_true")
parser.add_argument("-lu", "--leaveunlocked", action="store_true")
parser.add_argument("-ssf", "--skipsanford", action="store_true")
parser.add_argument("-sbl", "--skipbithlo", action="store_true")

args = parser.parse_args()

if args.date:
    date_str = args.date
else:
    # get yesterday's date
    yesterday = date.today() - timedelta(days=1)
    date_str = datetime.fromordinal(yesterday.toordinal()).strftime("%m-%d-%Y")

####### SANFORD DAILY DATA
if not args.skipsanford:
    # check if report has already been downloaded
    files = os.listdir(output_path)
    report_filename = "Report_by_client_" + date_str + ".xlsx"

    # delete any existing reports
    if report_filename in files:
        subprocess.run(["rm {0}".format(report_filename)], shell=True)

    # download yesterday's report
    print("RUNNING: Downloading SANFORD report from the SALT Web App")
    subprocess.run(["/usr/bin/python3 salt/run_daily_report.py -l \"SEM\" -d {0}".format(date_str)], shell=True)
    time.sleep(5)

    # double check that report has been downloaded / exists
    report_path = output_path + report_filename
    if not os.path.exists(report_path):
        print("ERROR: Downloaded report from SALT cannot be found")
        quit()

    # download pretty xlsx file to upload to drive
    print("RUNNING: Processing simplified report file")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l SEM -f {0} -m".format(report_path)], shell=True)

    # start first run of automation
    print("RUNNING: Starting first run of automation for SANFORD")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l SEM -f {0} -a".format(report_path)], shell=True)

    # run the failed entries
    location = "SEM"
    failed_report_filename = location + "_Failed_entries_" + date_str + ".xlsx"
    failed_report_path = output_path + failed_report_filename

    if not os.path.exists(failed_report_path):
        print("Failed entry report for SANFORD from SALT cannot be found, continuing data entry")
    else:
        print("\nRUNNING: Automating failed SANFORD entries")
        subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l SEM -f {0} -a".format(failed_report_path)], shell=True)

        # upload final instance of the failed entry report to drive
        gauth = GoogleAuth() 
        drive = GoogleDrive(gauth)

        gfile = drive.CreateFile({'parents': [{'id': '15sT6EeVyeUsMd_vinRYgSpncosPW7B2s'}], 'title': failed_report_filename}) 
        gfile.SetContentFile(failed_report_path)
        gfile.Upload()

    # delete report file from sanford location
    subprocess.run(["rm {0}".format(report_path)], shell=True)

    print("SUCCESS: Finished running Sanford entries!\n")

'''
####### BITHLO DAILY DATA
if not args.skipbithlo:
    # check if report has already been downloaded
    files = os.listdir(output_path)
    report_filename = "Report_by_client_" + date_str + ".xlsx"

    # delete any existing reports
    if report_filename in files:
        subprocess.run(["rm {0}".format(report_filename)], shell=True)

    # download yesterday's report
    print("RUNNING: Downloading BITHLO report from the SALT Web App")
    subprocess.run(["/usr/bin/python3 salt/run_daily_report.py -l \"BIT\" -d {0}".format(date_str)], shell=True)
    time.sleep(5)

    # double check that report has been downloaded / exists
    report_path = output_path + report_filename
    if not os.path.exists(report_path):
        print("ERROR: Downloaded report from SALT cannot be found")
        quit()

    # download pretty xlsx file to upload to drive
    print("RUNNING: Processing simplified report file")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l BIT -f {0} -m".format(report_path)], shell=True)

    # start first run of automation
    print("RUNNING: Starting first run of automation for SANFORD")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l BIT -f {0} -a".format(report_path)], shell=True)

    # run the failed entries
    location = "BIT"
    failed_report_filename = location + "_Failed_entries_" + date_str + ".xlsx"
    failed_report_path = output_path + failed_report_filename

    if not os.path.exists(failed_report_path):
        print("Failed entry report for BITHLO from SALT cannot be found, continuing data entry")
    else:
        print("\nRUNNING: Automating failed BITHLO entries")
        subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l BIT -f {0} -a".format(failed_report_path)], shell=True)

        # upload final instance of the failed entry report to drive
        gauth = GoogleAuth() 
        drive = GoogleDrive(gauth)

        gfile = drive.CreateFile({'parents': [{'id': '15sT6EeVyeUsMd_vinRYgSpncosPW7B2s'}], 'title': failed_report_filename}) 
        gfile.SetContentFile(failed_report_path)
        gfile.Upload()

    # delete report file from sanford location
    subprocess.run(["rm {0}".format(report_path)], shell=True)

    print("SUCCESS: Finished running BITHLO entries!\n")
'''

####### ORLANDO DAILY DATA
if not args.skipfirstrun:
    # check if report has already been downloaded
    files = os.listdir(output_path)
    report_filename = "Report_by_client_" + date_str + ".xlsx"

    # delete any existing reports
    if report_filename in files:
        subprocess.run(["rm {0}".format(report_filename)], shell=True)

    # download new report
    print("RUNNING: Downloading ORLANDO report from the SALT Web App")
    subprocess.run(["/usr/bin/python3 salt/run_daily_report.py -d {0}".format(date_str)], shell=True)
    time.sleep(5)

    # double check that report has been downloaded / exists
    report_path = output_path + report_filename
    if not os.path.exists(report_path):
        print("ERROR: Downloaded report from SALT cannot be found")
        quit()

    # download pretty xlsx file to upload to drive
    print("RUNNING: Processing simplified report file")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -f {0} -m".format(report_path)], shell=True)

    # start first run of automation
    print("RUNNING: Starting first run of automation for ORLANDO")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -f {0} -a".format(report_path)], shell=True)

# run the failed entries three more times
location = "ORL"
failed_report_filename = location + "_Failed_entries_" + date_str + ".xlsx"
failed_report_path = output_path + failed_report_filename

if not os.path.exists(failed_report_path):
    print("Failed entry report for ORLANDO from SALT cannot be found")
else:
    for i in range(run_count):
        print("\nRUNNING: Automating failed ORLANDO entries, {0} more round(s) to go".format(run_count-1-i))
        subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -f {0} -a".format(failed_report_path)], shell=True)

    # upload final instance of the failed entry report to drive
    gauth = GoogleAuth() 
    drive = GoogleDrive(gauth)

    gfile = drive.CreateFile({'parents': [{'id': '15sT6EeVyeUsMd_vinRYgSpncosPW7B2s'}], 'title': failed_report_filename}) 
    gfile.SetContentFile(failed_report_path)
    gfile.Upload()

# delete report from ORLANDO location
subprocess.run(["rm {0}".format(report_path)], shell=True)

####### ORLANDO 2.0 - NEW SALT APP - DAILY DATA
if not args.skipfirstrun:
    # check if report has already been downloaded
    files = os.listdir(output_path)

    year_str = args.date[6:10]
    month_str = args.date[0:2]
    day_str = args.date[3:5]
    date_str = year_str + '-' + month_str + '-' + day_str # fixed for rearranged date (why???)

    report_filename = "Export-" + date_str + ".xlsx"
    print(report_filename)

    # delete any existing reports
    if report_filename in files:
        subprocess.run(["rm {0}".format(report_filename)], shell=True)

    # double check that report has been downloaded / exists
    report_path = output_path + report_filename
    if not os.path.exists(report_path):
        print("ERROR: Downloaded report from SALT 2.0 - NEW WEB APP cannot be found")
        quit()

    # download pretty xlsx file to upload to drive
    print("RUNNING: Processing simplified report file")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l ORL2.0 -f {0} -m".format(report_path)], shell=True)

    # start first run of automation
    print("RUNNING: Starting first run of automation for ORLANDO 2.0")
    subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l ORL2.0 -f {0} -a".format(report_path)], shell=True)

# run the failed entries three more times
location = "ORL2.0"
failed_report_filename = location + "_Failed_entries_" + date_str + ".xlsx"
failed_report_path = output_path + failed_report_filename

if not os.path.exists(failed_report_path):
    print("Failed entry report for ORLANDO 2.0 from SALT cannot be found")
else:
    for i in range(run_count):
        print("\nRUNNING: Automating failed ORLANDO 2.0 entries, {0} more round(s) to go".format(run_count-1-i))
        subprocess.run(["/usr/bin/python3 salt/run_daily_data.py -l ORL2.0 -f {0} -a".format(failed_report_path)], shell=True)

    # upload final instance of the failed entry report to drive
    gauth = GoogleAuth() 
    drive = GoogleDrive(gauth)

    gfile = drive.CreateFile({'parents': [{'id': '15sT6EeVyeUsMd_vinRYgSpncosPW7B2s'}], 'title': failed_report_filename}) 
    gfile.SetContentFile(failed_report_path)
    gfile.Upload()

# delete report from ORLANDO location
subprocess.run(["rm {0}".format(report_path)], shell=True)

####### END OF AUTOMATION
print("SUCCESS: Finished running scheduled automation!")
# lock mac when done
if not args.leaveunlocked:
    os.system("pmset displaysleepnow")