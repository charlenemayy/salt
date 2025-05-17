from datetime import datetime
import re
import hmis_driver
import pandas as pd
import json

'''
Processes the data from the SALT Web App and preps it for Selenium automation 
in hmis_driver.py. Uses pandas to clean excel data retrieved from SALT 1.0.
This will likely be very subject to change as the report style changes with 
SALT 2.0. 
'''
class DailyData:
    # Orlando Item Keys
    service_item_codes_orl = ['Shower', 'Laundry']
    clothing_item_codes_orl = ['top', 'btm', 'und', 'sks', 'sho', 'bxr', 'diabetic socks', 'backpacks', 'belts']
    grooming_item_codes_orl = ['ddr', 'tbr', 'tps', 'razors', 'adult depends', 'band aid', 'tampons', 'bar soap', 
                               'deodorant', 'qtips', 'hygiene bag', 'comb', 'nail clippers', 'q-tips', 'conditioner',
                               'chapstick']
    food_item_codes_orl = ['sbg']
    bedding_item_codes_orl = ['blankets']
    electronic_item_codes_orl = ['power bank', 'batteries', 'earphones']
    homebased_item_codes_orl = ['highlighters', 'printing paper', 'reusable bag', 'reusable container', 'scotch tape',
                                   'sharpies']
    petgoods_item_codes_orl = ['cat food', 'dog food']
    loungeaccess_item_codes_orl = []

    # Sanford Item Keys
    service_item_codes_sem = ['shower', 'laundry']
    clothing_item_codes_sem = ['black bags', 'men\'s pant', 'men\'s top', 'shoes', 'socks', 'underwear', 
                           'women\'s bottom', 'women\'s top', 'boxer', 'clothing']
    grooming_item_codes_sem = ['feminine pads', 'hygiene bag', 'razors', 'soap bars', 'tampons', 'toothbrush',
                           'toothpaste', 'deodorant']
    food_item_codes_sem = ['snack', 'water']
    bedding_item_codes_sem = ['tent', 'blankets']
    electronic_item_codes_sem = ['power bank', 'batteries', 'earphones']
    homebased_item_codes_sem = ['highlighters', 'printing paper', 'reusable bag', 'reusable container', 'scotch tape',
                                   'sharpies']
    petgoods_item_codes_sem = ['cat food', 'dog food']
    loungeaccess_item_codes_sem = []

    # Bithlo Item Keys 
    service_item_codes_bit = ['shower', 'laundry']
    clothing_item_codes_bit = ['black bags', 'men\'s pant', 'men\'s top', 'shoes', 'socks', 'underwear', 
                           'women\'s bottom', 'women\'s top', 'boxer', 'clothing item']
    grooming_item_codes_bit = ['feminine pads', 'hygiene bag', 'razors', 'soap bars', 'tampons', 'toothbrush',
                           'toothpaste', 'deodorant', 'hygiene item']
    food_item_codes_bit = ['snack', 'water']
    bedding_item_codes_bit = ['tent', 'blankets']
    electronic_item_codes_bit = ['power bank', 'batteries', 'earphones']
    homebased_item_codes_bit = ['highlighters', 'printing paper', 'reusable bag', 'reusable container', 'scotch tape',
                                   'sharpies']
    petgoods_item_codes_bit = ['cat food', 'dog food']
    loungeaccess_item_codes_bit = []

    # Orlando 2.0 Item Keys
    service_item_codes_orl_2 = ['shower', 'laundry', 'inside shower', 'charging']
    clothing_item_codes_orl_2 = ['belt', 'bra', 'boxer', 'backpack', 'hat', 'jewelry', 'pants', 'purse', 'shirt', 'shoes', 
                                 'socks', 'sunglasses', 'ties', 'underwear', 'gloves', 'hand warmer', 'phone case', 'glasses',
                                 'scarf', 'suitcase', 'clothing item']
    grooming_item_codes_orl_2 = ['diapers', 'alcohol pad', 'aloe gel', 'band aid', 'soap', 'body lotion', 'body wash', 'wipes', 
                                 'chapstick', 'conditioner', 'condom', 'cotton ball', 'cotton gauze', 'deodorant', 
                                 'face mask', 'first aid', 'floss', 'brush', 'comb', 'hair gel', 'sanitizer', 'hygiene', 
                                 'ice packs', 'makeup', 'male guard', 'mini iphone fan', 'mirror', 'mouth wash', 'nail file', 
                                 'nail polish', 'nail trimmer', 'narcan', 'pad', 'perfume', 'pullups', 'q-tip', 'razor',
                                 'shaving cream', 'shower cap', 'sunscreen', 'tampon', 'tissue', 'toothbrush', 'toothpaste',
                                 'underpads', 'underwear', 'hygiene item']
    food_item_codes_orl_2 = ['snack bag']
    bedding_item_codes_orl_2 = ['blankets', 'ear plugs']
    electronics_item_codes_orl_2 = ['power bank', 'batteries', 'earphones']
    homebased_item_codes_orl_2 = ['highlighters', 'printing paper', 'reusable bag', 'reusable container', 'scotch tape',
                                   'sharpies']
    petgoods_item_codes_orl_2 = ['cat food', 'dog food']
    loungeaccess_item_codes_orl_2 = []
    information_item_codes_orl_2 = ['information']

    # Youth
    service_item_codes_yya = []
    clothing_item_codes_yya = ['clothing', 'socks', 'underwear']
    grooming_item_codes_yya = ['hygiene bag']
    food_item_codes_yya = ['snack bags']
    bedding_item_codes_yya = []
    electronics_item_codes_yya = []
    homebased_item_codes_yya = []
    petgoods_item_codes_yya = []
    loungeaccess_item_codes_yya = ['respite room']

    # Locations
    location_codes = ["BIT", "SEM", "ORL", "ORL2.0", "YYA"]

    def __init__(self, filename, automate, manual, show_output, location, list_items, skipfirstrow):
        self.automate = automate
        self.manual = manual
        self.show_output = show_output
        self.list_items = list_items
        self.unique_items = set()
        self.filename = filename
        self.location = location if location else "ORL"
        if self.location not in self.location_codes:
            print("Not a valid location code, please see README for details")
            quit()

        if (self.location == "ORL2.0" or self.location == "YYA") and skipfirstrow == True:
            self.df = pd.read_excel(io=filename,
                                 dtype={'': object,
                                        'DoB': object,
                                        'Client Name': object,
                                        'HMIS ID': object,
                                        'Services': object,
                                        'ITEMS': object},
                                        skiprows=[0])

            self.df = self.df.rename(columns={'Services': 'Service', 'ITEMS' : 'Items'})
        elif (self.location == "ORL2.0" or self.location == "YYA") and skipfirstrow == False:
            self.df = pd.read_excel(io=filename,
                                 dtype={'': object,
                                        'DoB': object,
                                        'Client Name': object,
                                        'HMIS ID': object,
                                        'Services': object,
                                        'ITEMS': object})

            self.df = self.df.rename(columns={'Services': 'Service', 'ITEMS' : 'Items'})
        else:
            self.df = pd.read_excel(io=filename,
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
        if self.df.empty:
            print("No data to enter into HMIS today, closing now")
            quit()

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
        if self.automate:
            self.driver = hmis_driver.Driver()
            self.driver.open_clienttrack()
            if not self.driver.login_clienttrack(self.username, self.password):
                print("Could not login successfully")
                return

        self.__clean_dataframe(['Race', 'Ethnicity', 'Verification of homeless', 'Gross monthly income'], 
                               ['', 'HMIS ID', 'Client Name', 'Service', 'Items', 'DoB'])

        # add new column combining items and services columns
        self.df['Services'] = ""
        for row_index in range(0, len(self.df)):
            # build dictionary datatype for client to pass into automation
            client_dict = {}
            row = self.df.iloc[row_index]

            # IF EMPTY ROW
            if isinstance(row['Client Name'], float):
                self.failed_df = self.failed_df.drop([row_index])
                continue

            # rearrange birthday and update row
            if not isinstance(row['DoB'], float):
                if isinstance(row['DoB'], datetime):
                    dt = row['DoB'].date()
                    date = dt.strftime('%m-%d-%Y')
                else:
                    date = row['DoB']

                if self.location == "ORL2.0" or self.location == "YYA":
                    client_dict['DoB'] = date
                else: # rearrange birthdate if not the new salt app
                    day = date[0:3]
                    month = date[3:6]
                    client_dict['DoB'] = month + day + date[6:(len(date))]

                # # update sheet for readability
                self.df.at[row_index, 'DoB'] = client_dict['DoB']

            # get total number of services and items
            services_dict = self.__get_service_totals(row)
            items_dict = self.__count_item_totals(row, services_dict)
            client_dict['Services'] = {**services_dict, **items_dict}
            # update sheet for readability
            self.df.at[row_index, 'Services'] = self.__clean_dictionary_string(str(client_dict['Services']))

            # split name into first and last and strip any trailing whitespaces and nicknames in quotes
            # an entry like "Edward Powell James" -> "Edward Powell, James" (Last, First)
            # no_quotes_name = re.sub('(".*")', "", row['Client Name'])
            # OR:
            # just remove quotes, as it might be a potential middle name
            if isinstance(row['Client Name'], float):
                row['Client Name'] = ''

            no_special_char_name = re.sub(r'[^a-zA-Z0-9\s]', '', row['Client Name'])
            stripped_name = no_special_char_name.strip()
            string_list = stripped_name.rsplit(' ', 1)

            if self.location == 'ORL2.0' or self.location == "YYA":
                if len(string_list) > 1:
                    client_dict['Last Name'] = string_list[1]
                else:
                    client_dict['Last Name'] = ''
                client_dict['First Name'] = string_list[0]
            else:
                if len(string_list) > 1:
                    client_dict['First Name'] = string_list[1]
                else:
                    client_dict['First Name'] = ''
                client_dict['Last Name'] = string_list[0]

            if isinstance(row['HMIS ID'], float):
                client_dict['Client ID'] = ''
            elif isinstance(row['HMIS ID'], int):
                client_dict['Client ID'] = str(row['HMIS ID']) 
            elif len(row['HMIS ID']) > 9: # encrypted id
                client_dict['Client ID'] = ''
            elif row['HMIS ID'] == '0' or row['HMIS ID'] == '000000' or any(c.isalpha() for c in row['HMIS ID']): #0 or 'no id' (why is this allowed???)
                client_dict['Client ID'] = ''
            else:
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
        
        # Close the browser
        if self.automate:
            self.driver.close_browser()

        if self.list_items:
            print(self.unique_items)

        # Make data more readable for manual data entry
        if self.manual:
            self.__clean_dataframe(['Service', 'Items'], ['', 'HMIS ID', 'Client Name', 'Services', 'DoB'])
            self.__export_manual_entry_data()

    def __automate_service_entry(self, client_dict, row_index):
        print("\nEntering Client:" + client_dict['First Name'], client_dict['Last Name'])
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
            loungeaccess_item_codes = DailyData.loungeaccess_item_codes_orl
            information_item_codes = []
        elif self.location == 'SEM':
            clothing_item_codes = DailyData.clothing_item_codes_sem
            grooming_item_codes = DailyData.grooming_item_codes_sem
            food_item_codes = DailyData.food_item_codes_sem
            bedding_item_codes = DailyData.bedding_item_codes_sem
            electronics_item_codes = DailyData.electronic_item_codes_sem
            homebased_item_codes = DailyData.homebased_item_codes_sem
            petgoods_item_codes = DailyData.petgoods_item_codes_sem
            loungeaccess_item_codes = DailyData.loungeaccess_item_codes_sem
            information_item_codes = []
        elif self.location == 'BIT':
            clothing_item_codes = DailyData.clothing_item_codes_bit
            grooming_item_codes = DailyData.grooming_item_codes_bit
            food_item_codes = DailyData.food_item_codes_bit
            bedding_item_codes = DailyData.bedding_item_codes_bit
            electronics_item_codes = DailyData.electronic_item_codes_bit
            homebased_item_codes = DailyData.homebased_item_codes_bit
            petgoods_item_codes = DailyData.petgoods_item_codes_bit
            loungeaccess_item_codes = DailyData.loungeaccess_item_codes_bit
            information_item_codes = []
        if self.location == 'ORL2.0' or self.location == 'YYA': # for new salt app
            clothing_item_codes = DailyData.clothing_item_codes_orl_2
            grooming_item_codes = DailyData.grooming_item_codes_orl_2
            food_item_codes = DailyData.food_item_codes_orl_2
            bedding_item_codes = DailyData.bedding_item_codes_orl_2
            electronics_item_codes = DailyData.electronics_item_codes_orl_2
            homebased_item_codes = DailyData.homebased_item_codes_orl_2
            petgoods_item_codes = DailyData.petgoods_item_codes_orl_2
            loungeaccess_item_codes = DailyData.loungeaccess_item_codes_orl_2
            information_item_codes = DailyData.information_item_codes_orl_2
        '''
        elif self.location == 'YYA':
            clothing_item_codes = DailyData.clothing_item_codes_yya
            grooming_item_codes = DailyData.grooming_item_codes_yya
            food_item_codes = DailyData.food_item_codes_yya
            bedding_item_codes = DailyData.bedding_item_codes_yya
            electronics_item_codes = DailyData.electronics_item_codes_yya
            homebased_item_codes = DailyData.homebased_item_codes_yya
            petgoods_item_codes = DailyData.petgoods_item_codes_yya
            loungeaccess_item_codes = DailyData.loungeaccess_item_codes_yya
            information_item_codes = []
        '''
        # TODO: CHANGE YYA ITEMS

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
                    string_list = row_items.split(item, 1) # maxsplit: 1
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

            loungeaccess_count = 0
            for item in loungeaccess_item_codes:
                index = row_items.find(item)
                if index >= 0:
                    string_list = row_items.split(item)
                    substring = string_list[1]

                    i = substring.index(':')
                    loungeaccess_count += int(substring[i+2])
                if loungeaccess_count > 0:
                    items_string = (items_string + "Lounge Access: " + str(loungeaccess_count) + "\n")
                    items_dict['Lounge Access'] = loungeaccess_count
                if self.show_output:
                    print("Lounge Access: " + str(loungeaccess_count))

            information_count = 0
            for item in information_item_codes:
                index = row_items.find(item)
                if index >= 0:
                    string_list = row_items.split(item)
                    substring = string_list[1]

                    i = substring.index(':')
                    information_count += int(substring[i+2])
                if information_count > 0:
                    items_string = (items_string + "Information: " + str(information_count) + "\n")
                    items_dict['Information'] = information_count
                if self.show_output:
                    print("Information: " + str(information_count))

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