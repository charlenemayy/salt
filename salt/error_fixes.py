from datetime import datetime
import re
import hmis_driver
import pandas as pd
import json

class ErrorFixes:

    def __init__(self, filename):
        self.filename = filename
        self.df = pd.read_excel(io=filename,
                             dtype={'Project ID': object,
                                    'Issue': object,
                                    'HMIS ID': object,
                                    'Entry Date': object})

        self.df = self.df.rename(columns={'Services': 'Service', 'ITEMS' : 'Items'})

        self.failed_df = self.df.copy()

        try:
            filename = "./salt/settings.json"
            f = open(filename)
            data = json.load(f)
        except Exception as e:
            print("ERROR: 'settings.json' file cannot be found, please see README for details")
            quit()

        settings = data["data"][0]
        self.username = settings["hmis_username"]
        self.password = settings["hmis_password"]
        self.output_path = settings["output_path"]

    # Parse each row and process client data
    def read_and_process_data(self):
        self.driver = hmis_driver.Driver()
        self.driver.open_clienttrack()
        if not self.driver.login_clienttrack(self.username, self.password):
            print("Could not login successfully")
            return

        for row_index in range(0, len(self.df)):
            # build dictionary datatype for client to pass into automation
            client_dict = {}
            row = self.df.iloc[row_index]

            # ensure HMIS ID in right format
            if isinstance(row['HMIS ID'], float):
                client_dict['Client ID'] = str(row['HMIS ID'])
            elif isinstance(row['HMIS ID'], int):
                client_dict['Client ID'] = str(row['HMIS ID']) 
            elif len(row['HMIS ID']) > 9: # encrypted id
                client_dict['Client ID'] = ''
            else:
                client_dict['Client ID'] = row['HMIS ID']

            # set Client Name to bypass check
            client_dict['Client Name'] = ''

            # format dates (if necessary)
            client_dict['Entry Date'] = row['Entry Date']

            # transfer remaining data
            client_dict['Project ID'] = row['Project ID']

            # go to corresponding error fix workflow
            client_dict['Issue'] = row['Issue']
            client_dict['Project Name'] = row['Project Name']

            self.__automate_enrollment_entry_assessment_fix(client_dict, row_index)

        # For Loop End

    def __automate_enrollment_entry_assessment_fix(self, client_dict, row_index):
        print("\nFixing Error for Client:" + client_dict['Client ID'])
        success = False
        # STEP ONE: SEARCH FOR CLIENT
        if not isinstance(client_dict['Client ID'], float) and client_dict['Client ID'] != "":
            success = self.driver.search_client_by_ID(client_dict['Client ID'], '', '')
        else:
            print("Not enough data provided to search for client:")
            print(client_dict)
            return

        if not success:
            print("Client could not be found in the system:")
            print(client_dict)
            return
        
        # STEP TWO: START WORKFLOW
        viable_enrollment_list = [client_dict['Project Name']]
        success = self.driver.fix_enrollment_entry_assessment(client_dict['Project ID'], viable_enrollment_list, client_dict['Entry Date'])
        if not success:
            print("Enrollment entry assessment could not be fixed")
            print(client_dict)
            return

        # remove client from list of failed automated entries
        self.failed_df = self.failed_df.drop([row_index])
        print("Success! " + str(len(self.failed_df.index)) + " entries remaining")
        self.__export_failed_automation_data()

    # Export a sheet of the failed automated entries in their original format
    # This way we can keep looping the failed entries and try again
    def __export_failed_automation_data(self):
        # get date from original file and output into new excel sheet
        output_name = (self.location + "_Failed_entries_" 
                       + self.filename)

        # create sheet for remaining clients that need to be entered and could not be automated
        self.failed_df.to_excel(self.output_path + output_name + ".xlsx", sheet_name = "Failed Entries Report - " + output_name)