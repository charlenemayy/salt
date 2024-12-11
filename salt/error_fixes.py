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

            # if empty row
            if isinstance(row['Client Name'], float):
                self.failed_df = self.failed_df.drop([row_index])
                continue

            # ensure HMIS ID in right format
            if isinstance(row['HMIS ID'], float):
                client_dict['Client ID'] = ''
            elif isinstance(row['HMIS ID'], int):
                client_dict['Client ID'] = str(row['HMIS ID']) 
            elif len(row['HMIS ID']) > 9: # encrypted id
                client_dict['Client ID'] = ''
            elif row['HMIS ID'] == '0' or any(c.isalpha for c in row['HMIS ID']): #0 or 'no id' (why is this allowed???)
                client_dict['Client ID'] = ''
            else:
                client_dict['Client ID'] = row['HMIS ID']

            # format dates (if necessary)
            client_dict['Entry Date'] = row['Entry Date']

            # transfer remaining data
            client_dict['Project ID'] = row['Project ID']

            # go to corresponding error fix workflow
            client_dict['Issue'] = row['Issue']

            if client_dict['Issue'] == "Missing Enrollment CoC":
                self.__automate_missing_enrollment_coc_fix(client_dict, row_index)
            elif client_dict['Issue'] == "":
                print("TODO")

        # For Loop End

    def __automate_missing_enrollment_coc_fix(self, client_dict, row_index):
        print("\nFixing Error for Client:" + client_dict['HMIS ID'])
        success = False
        # STEP ONE: SEARCH FOR CLIENT
        # Search by ID
        if not isinstance(client_dict['Client ID'], float) and client_dict['Client ID'] != "":
            success = self.driver.search_client_by_ID(client_dict['Client ID'], client_dict['First Name'], client_dict['Last Name'])
        # Search by DoB
        elif 'DoB' not in client_dict:
            print("Neither birthday or ID in data, can't search for client:")
            print(client_dict)
            return
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
        if self.location == "SEM":
            salt_enrollment_names = ["SALT Outreach-SEM Street Outreach"]
        elif self.location == "BIT":
            salt_enrollment_names = ["SALT Outreach-Bithlo Street Outreach"] 
        elif self.location == "YYA":
            salt_enrollment_names = ["SALT Outreach-YHDP Drop In Center"]
        else:
            salt_enrollment_names = ["SALT Outreach-ORL ESG Street Outreach", 
                                     "SALT Outreach-ORN ESG-CV Street Outreach",
                                     "SALT Outreach-ORN PSH Supportive Services",
                                     "SALT Outreach-ORL CDBG Services Only"]
        date = self.__get_date_from_filename(self.filename)
        service_date = str(date.strftime('%m%d%Y'))

        # enter client services for client - expects date with no non-numeric values (no dashes, etc.)``
        success = self.driver.enter_client_services(salt_enrollment_names, service_date, client_dict['Services'], self.location)
        if not success:
            print("Client services could not be entered into the system:")
            print(client_dict)
            return
        # remove client from list of failed automated entries
        self.failed_df = self.failed_df.drop([row_index])
        print("Success! " + str(len(self.failed_df.index)) + " entries remaining")
        self.__export_failed_automation_data()

    # Remove unecessary columns and reorganize for easier entry
    def __clean_dataframe(self, drop_columns, reorder_columns):
        self.df = self.df.drop(columns=drop_columns, axis=1, errors='ignore')
        reorder = reorder_columns
        self.df = self.df.reindex(columns=reorder)

    # Convert row values to proper data types and return a dictionary
    def __get_service_totals(self, row):
        services_dict = {}

        if isinstance(row['Service'], float):
            return services_dict
        else:
            index = row['Service'].lower().find('shower')
            if index >= 0:
                # find num value attributed to shower
                string_list = row['Service'].lower().split('shower')
                substring = string_list[1]

                # get first ':' following 'Shower'
                i = substring.index(':')
                services_dict['Shower'] = int(substring[i+2])

            index = row['Service'].lower().find('laundry')
            if index >= 0:
                # find num value attributed to laundry
                string_list = row['Service'].lower().split('laundry')
                substring = string_list[1]

                # get first ':' following 'Laundry' ()
                # multiply laundry x2 (one wash, one dry)
                i = substring.index(':')
                services_dict['Laundry'] = int(substring[i+2]) * 2

            index = row['Service'].lower().find('charging')
            if index >= 0:
                string_list = row['Service'].lower().split('charging')
                substring = string_list[1]

                i = substring.index(':')
                services_dict['Device Charging'] = int(substring[i+2])

            index = row['Service'].lower().find('case management')
            if index >= 0:
                string_list = row['Service'].lower().split('case management')
                substring = string_list[1]

                i = substring.index(':')
                services_dict['Case Management'] = int(substring[i+2])
            else: # sometimes case management is just 'case' (why ??????)
                index = row['Service'].lower().find('case')
                if index >= 0:
                    string_list = row['Service'].lower().split('case')
                    substring = string_list[1]

                    i = substring.index(':')
                    services_dict['Case Management'] = int(substring[i+2])


            index = row['Service'].lower().find('hope and help')
            if index >= 0:
                # find num value attributed to laundry
                string_list = row['Service'].lower().split('hope and help')
                substring = string_list[1]


                i = substring.index(':')
                services_dict['Healthcare'] = int(substring[i+2])

        return services_dict

    # Collect total number of items under each category for each client
    # and store all items into a dictionary
    def __count_item_totals(self, row, services_dict):
        items_dict = {}
        row_items = row['Items']

        if self.location == 'ORL':
            clothing_item_codes = DailyData.clothing_item_codes_orl
            grooming_item_codes = DailyData.grooming_item_codes_orl
            food_item_codes = DailyData.food_item_codes_orl
            bedding_item_codes = DailyData.bedding_item_codes_orl
            electronics_item_codes = DailyData.electronic_item_codes_orl
            homebased_item_codes = DailyData.homebased_item_codes_orl
            petgoods_item_codes = DailyData.petgoods_item_codes_orl
        elif self.location == 'SEM':
            clothing_item_codes = DailyData.clothing_item_codes_sem
            grooming_item_codes = DailyData.grooming_item_codes_sem
            food_item_codes = DailyData.food_item_codes_sem
            bedding_item_codes = DailyData.bedding_item_codes_sem
            electronics_item_codes = DailyData.electronic_item_codes_sem
            homebased_item_codes = DailyData.homebased_item_codes_sem
            petgoods_item_codes = DailyData.petgoods_item_codes_sem
        elif self.location == 'BIT':
            clothing_item_codes = DailyData.clothing_item_codes_bit
            grooming_item_codes = DailyData.grooming_item_codes_bit
            food_item_codes = DailyData.food_item_codes_bit
            bedding_item_codes = DailyData.bedding_item_codes_bit
            electronics_item_codes = DailyData.electronic_item_codes_bit
            homebased_item_codes = DailyData.homebased_item_codes_bit
            petgoods_item_codes = DailyData.petgoods_item_codes_bit
        if self.location == 'ORL2.0': # for new salt app
            clothing_item_codes = DailyData.clothing_item_codes_orl_2
            grooming_item_codes = DailyData.grooming_item_codes_orl_2
            food_item_codes = DailyData.food_item_codes_orl_2
            bedding_item_codes = DailyData.bedding_item_codes_orl_2
            electronics_item_codes = DailyData.electronics_item_codes_orl_2
            homebased_item_codes = DailyData.homebased_item_codes_orl_2
            petgoods_item_codes = DailyData.petgoods_item_codes_orl_2
        elif self.location == 'YYA':
            clothing_item_codes = DailyData.clothing_item_codes_yya
            grooming_item_codes = DailyData.grooming_item_codes_yya
            food_item_codes = DailyData.food_item_codes_yya
            bedding_item_codes = DailyData.bedding_item_codes_yya
            electronics_item_codes = DailyData.electronics_item_codes_yya
            homebased_item_codes = DailyData.homebased_item_codes_yya
            petgoods_item_codes = DailyData.petgoods_item_codes_yya

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

            row_items = row_items.lower()
            items_string = ""

            # Clothing 
            clothing_count = 0
            for item in clothing_item_codes:
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
            for item in grooming_item_codes:
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
            for item in food_item_codes:
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
            for item in bedding_item_codes:
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

            # Electronics 
            electronics_count = 0
            for item in electronics_item_codes:
                index = row_items.find(item)
                if index >= 0:
                    # find num value attributed to item code
                    string_list = row_items.split(item)
                    substring = string_list[1]

                    # get first ':' following item code
                    i = substring.index(':')
                    electronics_count += int(substring[i+2])
            if electronics_count > 0:
                items_string = (items_string + "Electronics: " + str(electronics_count) + "\n")
                items_dict['Electronics'] = electronics_count
            if self.show_output: 
                print("Electronics: " + str(electronics_count))

            # Home Based 
            homebased_count = 0
            for item in homebased_item_codes:
                index = row_items.find(item)
                if index >= 0:
                    # find num value attributed to item code
                    string_list = row_items.split(item)
                    substring = string_list[1]

                    # get first ':' following item code
                    i = substring.index(':')
                    homebased_count += int(substring[i+2])
            if homebased_count > 0:
                items_string = (items_string + "Home Based: " + str(homebased_count) + "\n")
                items_dict['Home Based'] = homebased_count
            if self.show_output: 
                print("Home Based: " + str(homebased_count))

            # Pet Goods 
            petgoods_count = 0
            for item in petgoods_item_codes:
                index = row_items.find(item)
                if index >= 0:
                    # find num value attributed to item code
                    string_list = row_items.split(item)
                    substring = string_list[1]

                    # get first ':' following item code
                    i = substring.index(':')
                    petgoods_count += int(substring[i+2])
            if petgoods_count > 0:
                items_string = (items_string + "Pet Goods: " + str(petgoods_count) + "\n")
                items_dict['Pet Goods'] = petgoods_count
            if self.show_output: 
                print("Pet Goods: " + str(petgoods_count))

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
        '''
        if self.location == "ORL2.0":
            date_string = re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", filename)
            original_date = datetime.strptime(date_string[0], '%Y-%m-%d')
            str_date = original_date.strftime('%m-%d-%Y')
            date = datetime.strptime(str_date, '%m-%d-%Y')
        else:
            date_string = re.search("([0-9]{2}\-[0-9]{2}\-[0-9]{4})", filename)
            date = datetime.strptime(date_string[0], '%m-%d-%Y')
        '''
        return date

    # Export cleaned and readable spreadsheet for data to be entered manually
    def __export_manual_entry_data(self):
        # get date from original file and output into new excel sheet
        date = self.__get_date_from_filename(self.filename)
        output_name = str(date.strftime('%d')) + ' ' + str(date.strftime('%b')) + ' ' + str(date.strftime('%Y') + " - " + self.location)

        # format: '01 Jan 2024.xlsx'
        self.df.to_excel(self.output_path + output_name + ".xlsx", sheet_name=output_name)

    # Export a sheet of the failed automated entries in their original format
    # This way we can keep looping the failed entries and try again
    def __export_failed_automation_data(self):
        # get date from original file and output into new excel sheet
        date = self.__get_date_from_filename(self.filename)
        output_name = (self.location + "_Failed_entries_" 
                       + str(date.strftime('%m')) + '-' 
                       + str(date.strftime('%d')) + '-' 
                       + str(date.strftime('%Y')))

        # create sheet for remaining clients that need to be entered and could not be automated
        self.failed_df.to_excel(self.output_path + output_name + ".xlsx", sheet_name = "Failed Entries Report - " + output_name)