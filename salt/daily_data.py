from datetime import datetime
import re
import automation_driver
import pandas as pd

class DailyData:
    # Item Keys - Clothing, Grooming, Food, Bedding
    service_item_codes = ['Shower', 'Laundry']
    clothing_item_codes = ['TOP', 'BTM', 'UND', 'SKS', 'SHO', 'BXR', 'Diabetic Socks', 'Backpacks']
    grooming_item_codes = ['DDR', 'TBR', 'TPS', 'Razors', 'Adult Depends', 'Band Aid', 'Tampons']
    food_item_codes = ['SBG']
    bedding_item_codes = ['Blankets']

    # Login Info
    username = "charlene@saltoutreach.org"
    password = "1ntsygtmtir!CL"

    def __init__(self, df, filename, automate, manual, show_output, list_items):
        self.df = df
        self.automate = automate
        self.manual = manual
        self.show_output = show_output
        self.list_items = list_items
        self.unique_items = set()
        self.filename = filename

        # on successful automated entry for a client, drop the row from this dataframe
        self.failed_df = self.df.copy()
                
        if self.automate:
            self.driver = automation_driver.Driver()
            self.driver.open_clienttrack()
            self.driver.login_clienttrack(DailyData.username, DailyData.password)

    # Parse each row and process client data
    def read_and_process_data(self):
        self.__clean_dataframe(['Race', 'Ethnicity', 'Verification of homeless', 'Gross monthly income'], 
                               ['', 'HMIS ID', 'Client Name', 'Service', 'Items', 'DoB'])
        # add new column combining items and services columns
        self.df['Services'] = ""
        for row_index in range(0, len(self.df)):
            # build dictionary datatype for client to pass into automation
            client_dict = {}
            row = self.df.iloc[row_index]

            '''
            # rearrange birthday and update row
            if not isinstance(row['DoB'], float):
                date = row['DoB']
                day = date[0:3]
                month = date[3:6]
                client_dict['DoB'] = month + day + date[6:(len(date))]
                # update sheet for readability
                self.df.at[row_index, 'DoB'] = client_dict['DoB']
            '''

            # TODO: LOGIC FOR SHOWER ENTRIES
            client_dict['DoB'] = row['DoB']

            # get total number of services and items
            services_dict = self.__get_service_totals(row, row_index)
            items_dict = self.__count_item_totals(row, row_index, services_dict)
            client_dict['Services'] = {**services_dict, **items_dict}
            # update sheet for readability
            self.df.at[row_index, 'Services'] = self.__clean_dictionary_string(str(client_dict['Services']))

            # split name into first and last and strip any trailing whitespaces and nicknames in quotes
            # an entry like "Edward Powell James" -> "Edward Powell, James" (Last, First)
            # no_quotes_name = re.sub('(".*")', "", row['Client Name'])
            # OR:
            # just remove quotes, as it might be a potential middle name
            no_quotes_name = row['Client Name'].replace('"', '')
            stripped_name = no_quotes_name.strip()
            string_list = stripped_name.rsplit(' ', 1)
            if len(string_list) > 1:
                client_dict['First Name'] = string_list[1]
            else:
                client_dict['First Name'] = ''
            client_dict['Last Name'] = string_list[0]

            # add remaining client info
            client_dict['Client ID'] = row['HMIS ID']

            if self.show_output:
                print()
                print("Final Dictionary Output:")
                print(client_dict)
                print("-----------------------------")

            # automate data entry for current client (as represented by the current row)
            if self.automate:
                self.__automate_service_entry(client_dict, row_index)
        # For Loop End

        if self.list_items:
            print(self.unique_items)

        # Make data more readable for manual data entry
        self.__clean_dataframe(['Service', 'Items'], ['', 'HMIS ID', 'Client Name', 'Services', 'DoB'])

    def __automate_service_entry(self, client_dict, row_index):
        print("\nEntering Client:" + client_dict['First Name'], client_dict['Last Name'])
        success = False
        # STEP ONE: SEARCH FOR CLIENT
        # Search by ID
        if not isinstance(client_dict['Client ID'], float) and client_dict['Client ID'] != "":
            success = self.driver.search_client_by_ID(client_dict['Client ID'], client_dict['First Name'], client_dict['Last Name'])
        # Search by DoB
        elif not isinstance(client_dict['DoB'], float) and client_dict['DoB'] != "":
            success = self.driver.search_client_by_birthdate(client_dict['DoB'], client_dict['First Name'], client_dict['Last Name'])
        # Lack of Info
        else:
            print("Not enough data provided to search for client:")
            print(client_dict)
            return

        if not success:
            print("Client could not be found in the system:")
            print(client_dict)
            return
        
        # STEP TWO: ENTER SERVICES FOR CLIENT
        # order matters - from most desirable option to last
        salt_enrollment_names = ["SALT Outreach-ORL ESG Street Outreach", 
                                 "SALT Outreach-ORN ESG-CV Street Outreach",
                                 "SALT Outreach-ORN PSH Supportive Services",
                                 "SALT Outreach-ORL CDBG Services Only"]
        date = self.__get_date_from_filename(self.filename)
        service_date = str(date.strftime('%m%d%Y'))

        # enter client services for client - expects date with no non-numeric values (no dashes, etc.)``
        success = self.driver.enter_client_services(salt_enrollment_names, service_date, client_dict['Services'])
        if not success:
            print("Client services could not be entered into the system:")
            print(client_dict)
            return
        # remove client from list of failed automated entries
        self.failed_df = self.failed_df.drop([row_index])
        self.export_failed_automation_data("~/Downloads/")

    # Remove unecessary columns and reorganize for easier entry
    def __clean_dataframe(self, drop_columns, reorder_columns):
        self.df = self.df.drop(columns=drop_columns, axis=1)
        reorder = reorder_columns
        self.df = self.df.reindex(columns=reorder)

    # Convert row values to proper data types and return a dictionary
    def __get_service_totals(self, row, row_index):
        services_dict = {}

        if isinstance(row['Service'], float):
            return services_dict
        else:
            index = row['Service'].find('Shower')
            if index >= 0:
                # find num value attributed to shower
                string_list = row['Service'].split('Shower')
                substring = string_list[1]

                # get first ':' following 'Shower'
                i = substring.index(':')
                services_dict['Shower'] = int(substring[i+2])

            index = row['Service'].find('Laundry')
            if index >= 0:
                # find num value attributed to laundry
                string_list = row['Service'].split('Laundry')
                substring = string_list[1]

                # get first ':' following 'Laundry' ()
                # multiply laundry x2 (one wash, one dry)
                i = substring.index(':')
                services_dict['Laundry'] = int(substring[i+2]) * 2

        return services_dict

    # Collect total number of items under each category for each client
    # and store all items into a dictionary
    def __count_item_totals(self, row, row_index, services_dict):
        items_dict = {}
        row_items = row['Items']

        if self.show_output:
            print("Raw Excel Data:")
            print("SERVICES")
            print(row['Service'])
            print("ITEMS")
            print(row_items)
            print()
            print("Processed Item Counts:")

        if not isinstance(row_items, float):
            # OPTIONAL: collect all unique keys for items i.e. SHO, TOP, etc.
            if self.list_items:
                li = list(row_items.split(" "))
                for item in li:
                    if item.isalpha():
                        self.unique_items.add(item)

            items_string = ""

            # Clothing 
            clothing_count = 0
            for item in DailyData.clothing_item_codes:
                index = row_items.find(item)
                if index >= 0:
                    # find num value attributed to item code
                    string_list = row_items.split(item)
                    substring = string_list[1]

                    # get first ':' following item code
                    i = substring.index(':')
                    clothing_count += int(substring[i+2])
            if clothing_count > 0:
                items_string = (items_string + "Clothing: " + str(clothing_count) + "\n")
                items_dict['Clothing'] = clothing_count
            if self.show_output:
                print("Clothing: " + str(clothing_count))

            # Grooming/Hygiene
            grooming_count = 0
            for item in DailyData.grooming_item_codes:
                index = row_items.find(item)
                if index >= 0:
                    # find num value attributed to item code
                    string_list = row_items.split(item)
                    substring = string_list[1]

                    # get first ':' following item code
                    i = substring.index(':')
                    grooming_count += int(substring[i+2])
            # add body wash + shampoo for each shower
            if 'Shower' in services_dict:
                grooming_count += (services_dict['Shower'] * 2)
            if grooming_count > 0:
                items_string = (items_string + "Grooming: " + str(grooming_count) + "\n")
                items_dict['Grooming'] = grooming_count
            if self.show_output:
                print("Grooming: " + str(grooming_count))

            # Laundry Products
            laundry_product_count = 0
            if 'Laundry' in services_dict:
                # add detergent for each laundry run (wash + dry)
                laundry_product_count += int(services_dict['Laundry'] / 2)
            if laundry_product_count > 0:
                items_string = (items_string + "Laundry Products: " + str(laundry_product_count) + "\n")
                items_dict['Laundry Products'] = laundry_product_count
            if self.show_output:
                print("Laundry Products: " + str(grooming_count))

            # Food 
            food_count = 0
            for item in DailyData.food_item_codes:
                index = row_items.find(item)
                if index >= 0:
                    # find num value attributed to item code
                    string_list = row_items.split(item)
                    substring = string_list[1]

                    # get first ':' following item code
                    i = substring.index(':')
                    food_count += int(substring[i+2])
            if food_count > 0:
                items_string = (items_string + "Food: " + str(food_count) + "\n")
                items_dict['Food'] = food_count
            if self.show_output: 
                print("Food: " + str(food_count))

            # Bedding 
            bedding_count = 0
            for item in DailyData.bedding_item_codes:
                index = row_items.find(item)
                if index >= 0:
                    # find num value attributed to item code
                    string_list = row_items.split(item)
                    substring = string_list[1]

                    # get first ':' following item code
                    i = substring.index(':')
                    bedding_count += int(substring[i+2])
            if bedding_count > 0:
                items_string = (items_string + "Bedding: " + str(bedding_count) + "\n")
                items_dict['Bedding'] = bedding_count
            if self.show_output: 
                print("Bedding: " + str(bedding_count))
        # if there are no items in the item column but the service column is not empty
        elif (services_dict): 
            items_string = ""
            grooming_count = 0
            laundry_product_count = 0
            if 'Shower' in services_dict:
                grooming_count += (services_dict['Shower'] * 2)
            if grooming_count > 0:
                items_string = (items_string + "Grooming: " + str(grooming_count) + "\n")
                items_dict['Grooming'] = grooming_count
                if self.show_output:
                    print("Grooming: " + str(grooming_count))
            # add detergent for each laundry run (wash + dry)
            if 'Laundry' in services_dict:
                laundry_product_count += int(services_dict['Laundry'] / 2)
            if laundry_product_count > 0:
                items_string = (items_string + "Laundry Products: " + str(laundry_product_count) + "\n")
                items_dict['Laundry Products'] = laundry_product_count
                if self.show_output:
                    print("Laundry Products: " + str(laundry_product_count))

        return items_dict
    
    # Make dictionary string more readable
    def __clean_dictionary_string(self, string):
        rep = {"{" : "", "}" : "", ", " : "\n"}
        rep = dict((re.escape(k), v) for k, v in rep.items())
        pattern = re.compile("|".join(rep.keys()))
        return pattern.sub(lambda m: rep[re.escape(m.group(0))], string)
    
    # Expects to find substring in format MM-DD-YEAR; returns in format MM-DD-YEAR
    def __get_date_from_filename(self, filename):
        date_string = re.search("([0-9]{2}\-[0-9]{2}\-[0-9]{4})", filename)
        date = datetime.strptime(date_string[0], '%m-%d-%Y')
        return date

    # Export cleaned and readable spreadsheet for data to be entered manually
    def export_manual_entry_data(self, output_path):
        # get date from original file and output into new excel sheet
        date = self.__get_date_from_filename(self.filename)
        output_name = str(date.strftime('%d')) + ' ' + str(date.strftime('%b')) + ' ' + str(date.strftime('%Y'))

        # format: '01 Jan 2024.xlsx'
        self.df.to_excel(output_path + output_name + ".xlsx", sheet_name=output_name)

    # Export a sheet of the failed automated entries in their original format
    # This way we can keep looping the failed entries and try again
    def export_failed_automation_data(self, output_path):
        # get date from original file and output into new excel sheet
        date = self.__get_date_from_filename(self.filename)
        output_name = ("Failed Entries - " 
                       + str(date.strftime('%m')) + '-' 
                       + str(date.strftime('%d')) + '-' 
                       + str(date.strftime('%Y')))

        # create sheet for remaining clients that need to be entered and could not be automated
        self.failed_df.to_excel(output_path + output_name + ".xlsx", sheet_name = "Failed Entries Report - " + output_name)