import json
import salt_driver
from datetime import datetime
'''
'''
class DailyReport:

    def __init__(self, date, location):
        self.driver = salt_driver.Driver()
        self.date = date #MM-DD-YYYY
        self.location = location if location else "ORL"

        try:
            filename = "./salt/settings.json"
            f = open(filename)
            data = json.load(f)
        except Exception as e:
            print("ERROR: 'settings.json' file cannot be found, please see README for details")
            quit()

        settings = data["data"][0]
        self.username = settings["salt_username"]
        self.password = settings["salt_password"]
        self.output_path = settings["output_path"]
    
    def download_report(self):
        self.driver.open_saltwebapp(self.location)
        if not self.driver.login_saltwebapp_google(self.username, self.password):
            return
        # salt date search requires format YYYY-MM-DD
        date = datetime.strptime(self.date, "%m-%d-%Y").strftime("%Y-%m-%d")
        if not self.driver.navigate_to_daily_data_by_client(date):
            return
        self.driver.download_daily_report_by_client(self.location)
        self.driver.close_browser()