from datetime import datetime
import re
import hmis_driver
import pandas as pd
import json

'''
Processes the data from the SALT Web App and preps it for Selenium automation 
in hmis_driver.py. Uses pandas to clean csv data retrieved from SALT 1.0.
This will likely be very subject to change as the report style changes with 
SALT 2.0. 
'''
class DailyData:
    # Old Orlando Item Keys
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

    # Global Item Keys
    shower_item_codes = ['shower']
    laundry_item_codes = ['laundry']
    case_management_item_codes = ['case management']
    charging_item_codes = ['charging', 'charge']
    clothing_item_codes = ['belt', 'bra', 'boxer', 'backpack', 'hat', 'jewelry', 'pants', 'purse', 'shirt', 'shoes', 
                                 'socks', 'sunglasses', 'ties', 'underwear', 'gloves', 'hand warmer', 'phone case', 'glasses',
                                 'scarf', 'suitcase', 'clothing', 'bottom', 'top', 'black bags']
    grooming_item_codes = ['diapers', 'alcohol pad', 'aloe gel', 'band aid', 'soap', 'body wash', 'wipes', 
                                 'chapstick', 'conditioner', 'condom', 'cotton ball', 'cotton gauze', 'deodorant', 'lotion', 'pads'
                                 'face mask', 'first aid', 'floss', 'brush', 'comb', 'hair gel', 'sanitizer', 'hygiene item', 'hygiene bag' 
                                 'ice packs', 'makeup', 'male guard', 'mini iphone fan', 'mirror', 'mouth wash', 'nail file', 
                                 'nail polish', 'nail trimmer', 'nail care', 'narcan', 'pad', 'perfume', 'pullups', 'q-tip', 'razor', 'wipes'
                                 'shaving cream', 'shower cap', 'sunscreen', 'tampon', 'tissue', 'toothbrush', 'toothpaste',
                                 'underpads', 'underwear']
    food_item_codes = ['snack bag', 'coffee', 'meal', 'water', 'lunch plate']
    bedding_item_codes = ['blanket', 'ear plugs', 'tent']
    electronics_item_codes = ['power bank', 'batteries', 'earphones']
    homebased_item_codes = ['highlighters', 'printing paper', 'reusable bag', 'reusable container', 'scotch tape',
                                   'sharpies']
    petgoods_item_codes = ['cat food', 'dog food']
    lounge_access_item_codes = ['lounge access']
    information_item_codes = ['information']
    device_charging_item_codes = ['device charging']
    transportation_item_codes = ['transportation', 'bike repair']
    healthcare_item_codes = ['hope and help']
    storage_item_codes = ['storage']
    street_outreach_item_codes = ['general service']

    # Locations
    location_codes = ["BIT", "SEM", "ORL", "YYA", "APO"]

    def __init__(self, filename, automate, manual, show_output, list_items):
        self.automate = automate
        self.manual = manual
        self.show_output = show_output
        self.list_items = list_items
        self.unique_items = set()
        self.filename = filename
        self.export_version = "corsalisapp" #TODO: every version is on corsalis now until future notice

        if self.export_version == "corsalisapp":
            if 'Failed_entries' in self.filename:
                self.df = pd.read_excel(io=filename,
                     dtype={'': object,
                            'DoB': object,
                            'Client Name': object,
                            'HMIS ID': object,
                            'Services': object,
                            'ITEMS': object,
                            'Tags': object,
                            'Locations Visited': object})
            else:
                self.df = pd.read_csv(filename,
                                     dtype={'': object,
                                            'DoB': object,
                                            'Client Name': object,
                                            'HMIS ID': object,
                                            'Services': object,
                                            'ITEMS': object,
                                            'Tags': object,
                                            'Locations Visited': object},
                                            skiprows=4)

        if self.df.empty:
            print("No data to enter into HMIS today, closing now")
            quit()

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

        self.failed_df = self.df.copy()
        self.__export_failed_automation_data()

    # Parse each row and process client data
    def read_and_process_data(self):
        if self.automate:
            self.driver = hmis_driver.Driver()
            self.driver.open_clienttrack()
            if not self.driver.login_clienttrack(self.username, self.password):
                print("Could not login successfully")
                return
        
        if self.export_version == "corsalisapp":
            self.__clean_dataframe([], ['HMIS ID', 'Client Name', 'Services', 'ITEMS', 'DoB', 'Tags', 'Locations Visited'])
            self.df.rename(columns={'Services':'Service', 'ITEMS': 'Items'}, inplace=True)

        # add new column combining items and services columns
        self.df['Services'] = ""

        # START ROW PROCESSING
        row_index = 0
        while row_index < len(self.df):
            client_dict = {}
            row = self.df.iloc[row_index]

            # EMPTY ROW
            if isinstance(row['Client Name'], float):
                print("Skipping empty row...")
                self.failed_df = self.failed_df.drop([row_index])
                self.__export_failed_automation_data()
                row_index += 1
                continue

            # HMIS ID
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

            # BIRTHDAY - rearrange birthday and update row
            if not isinstance(row['DoB'], float):
                if isinstance(row['DoB'], datetime):
                    dt = row['DoB'].date()
                    date = dt.strftime('%m-%d-%Y')
                else:
                    date = row['DoB']

                if self.export_version == "corsalisapp":
                    client_dict['DoB'] = date
                else: # rearrange birthdate if not the new salt app
                    day = date[0:3]
                    month = date[3:6]
                    client_dict['DoB'] = month + day + date[6:(len(date))]

                self.df.at[row_index, 'DoB'] = client_dict['DoB']

            # CLIENT NAME
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

            if self.export_version == "corsalisapp":
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

            # TAGS - look for clients effected by hurricane, etc.
            client_dict['Tags'] = row['Tags'] if isinstance(row['Tags'], str) else ""

            # LOCATION 
            locations_visited = str(row['Locations Visited']).lower()

            # check if multiple locations were visited
            if ';' in locations_visited: 
                locations = locations_visited.split(';')
                for cur_location in locations:
                    no_special_char_name = re.sub(r'[^a-zA-Z0-9\s]', '', cur_location)
                    location = no_special_char_name.strip()

                    # add new row in dataframe for each location
                    new_row_data = {'':'', 'DoB':row['DoB'], 'Client Name': row['Client Name'], 'HMIS ID':row['HMIS ID'], 'Service':row['Service'], 'Items':row['Items'], 'Tags':row['Tags'], 'Locations Visited':location}
                    # new_row_data = {'':'', 'DoB':row['DoB'], 'Client Name': row['Client Name'], 'HMIS ID':row['HMIS ID'], 'Services':row['Service'], 'ITEMS':row['Items'], 'Tags':row['Tags'], 'Locations Visited':location}
                    new_row = pd.DataFrame([new_row_data])

                    insert_at_index = row_index + 1

                    df_part1 = self.df.iloc[:insert_at_index]
                    df_part2 = self.df.iloc[insert_at_index:]

                    self.df = pd.concat([df_part1, new_row, df_part2]).reset_index(drop=True)
                    # self.failed_df = self.df.copy()
                print("Successfully split multiple locations into new rows for client:", row['Client Name'], "continuing automation")
                self.failed_df = self.failed_df.drop([row_index])
                self.__export_failed_automation_data()
                row_index += 1
                continue
            else:
                location = locations_visited
            
            # check that location is valid
            valid_locations = {'powerhouse': 'ORL',
                               'apopka': 'APO',
                               'bithlo': 'BIT',
                               'youth and young adult': 'YYA',
                               'sanford rom': 'SEM',
                               'sanford fumc': 'SEM'}
            if location in valid_locations:
                client_dict['Location'] = valid_locations[location]
            else:
                print("Skipping invalid location", location)
                self.failed_df = self.failed_df.drop([row_index])
                self.__export_failed_automation_data()
                row_index += 1
                continue

            # SERVICES AND ITEMS 
            client_dict['Services'] = self.__count_service_and_item_totals(row, client_dict['Location'])
            self.df.at[row_index, 'Services'] = self.__clean_dictionary_string(str(client_dict['Services']))

            # OUTPUT
            if self.show_output:
                print()
                print("Final Dictionary Output:")
                print(client_dict)
                print("-----------------------------")

            # AUTOMATE ROW
            if self.automate:
                self.__automate_service_entry(client_dict, row_index)
            row_index += 1
        # While Loop End
        
        # Close the browser
        if self.automate:
            self.driver.close_browser()

        if self.list_items:
            print(self.unique_items)

        # Make data more readable for manual data entry
        if self.manual:
            self.__clean_dataframe(['Service', 'Items'], ['', 'HMIS ID', 'Client Name', 'Services', 'DoB', 'Locations Visited'])
            self.__export_manual_entry_data()

    def __automate_service_entry(self, client_dict, row_index):
        print("\nEntering Client: " + client_dict['First Name'], client_dict['Last Name'], "for", client_dict['Location'], "location")
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

        # set project to enroll client in
        # in most cases, PROJECT = LOCATION
        project = client_dict['Location']

        if "hurricane" in client_dict["Tags"].lower():
            salt_enrollment_names = ["SALT Outreach-Helene/Milton"]
            project = "HURRICANE"
        elif client_dict['Location'] == "SEM":
            salt_enrollment_names = ["SALT Outreach-SEM Street Outreach"]
        elif client_dict['Location'] == "BIT":
            salt_enrollment_names = ["SALT Outreach-Bithlo Street Outreach"] 
        elif client_dict['Location'] == "YYA":
            salt_enrollment_names = ["SALT Outreach-YHDP Drop In Center"]
        elif client_dict['Location'] == "APO":
            salt_enrollment_names = ["SALT Outreach-Apopka Street Outreach"]
        else:
            salt_enrollment_names = ["SALT Outreach-ORL ESG Street Outreach", 
                                     "SALT Outreach-ORN ESG-CV Street Outreach",
                                     "SALT Outreach-ORN PSH Supportive Services",
                                     "SALT Outreach-ORL CDBG Services Only"]
        date = self.__get_date_from_filename(self.filename)
        service_date = str(date.strftime('%m%d%Y'))

        # enter client services for client - expects date with no non-numeric values (no dashes, etc.)``
        success = self.driver.enter_client_services(salt_enrollment_names, service_date, client_dict['Services'], project, client_dict['Location'])
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

    # Collect total number of services and items under each category for each client
    # and store all items into a dictionary
    def __count_service_and_item_totals(self, row, location):

        shower_item_codes = DailyData.shower_item_codes
        laundry_item_codes = DailyData.laundry_item_codes
        case_management_item_codes = DailyData.case_management_item_codes
        clothing_item_codes = DailyData.clothing_item_codes
        grooming_item_codes = DailyData.grooming_item_codes
        food_item_codes = DailyData.food_item_codes
        bedding_item_codes = DailyData.bedding_item_codes
        electronics_item_codes = DailyData.electronics_item_codes
        homebased_item_codes = DailyData.homebased_item_codes
        petgoods_item_codes = DailyData.petgoods_item_codes
        lounge_access_item_codes = DailyData.lounge_access_item_codes
        information_item_codes = DailyData.information_item_codes
        device_charging_item_codes = DailyData.device_charging_item_codes
        transportation_item_codes = DailyData.transportation_item_codes
        healthcare_item_codes = DailyData.healthcare_item_codes
        storage_item_codes = DailyData.storage_item_codes
        street_outreach_item_codes = DailyData.street_outreach_item_codes
        
        if self.show_output:
            print("Raw CSV Data:")
            print("SERVICES")
            print(row['Service'])
            print("ITEMS")
            print(row['Items'])
            print()
            print("Processed Item Counts:")

        items_dict = {}

        if isinstance(row['Service'], float) and isinstance(row['Items'], float):
            return items_dict

        # if only one of the columns (Service or Items) is empty
        services_string = row['Service'] if isinstance(row['Service'], str) else ''
        items_string = row['Items'] if isinstance(row['Items'], str) else ''
        row_items = services_string + ' ' + items_string

        row_items = row_items.lower()
        items_string = ""

        # OPTIONAL: collect all unique keys for items i.e. SHO, TOP, etc.
        if self.list_items:
            li = list(row_items.split(" "))
            for item in li:
                if item.isalpha():
                    self.unique_items.add(item)

        # Shower
        shower_count = 0
        for item in shower_item_codes:
            index = row_items.find(item)
            if index >= 0:
                # find num value attributed to item code
                string_list = row_items.split(item, 1) # maxsplit: 1
                substring = string_list[1]

                # get first ':' following item code
                i = substring.index(':')
                if substring[i+2].isdigit():
                    shower_count += int(substring[i+2])
        if shower_count > 0:
            items_string = (items_string + "Shower: " + str(shower_count) + "\n")
            items_dict['Shower'] = shower_count
        if self.show_output:
            print("Shower: " + str(shower_count))

        # Laundry
        laundry_count = 0
        for item in laundry_item_codes:
            index = row_items.find(item)
            if index >= 0:
                # find num value attributed to laundry
                string_list = row_items.lower().split(item, 1)
                substring = string_list[1]

                # get first ':' following 'Laundry' ()
                # multiply laundry x2 (one wash, one dry)
                i = substring.index(':')
                if substring[i+2].isdigit():
                    laundry_count += int(substring[i+2]) * 2
            if laundry_count > 0:
                items_string = (items_string + "Laundry: " + str(laundry_count) + "\n")
                items_dict['Laundry'] = laundry_count
            if self.show_output:
                print("Laundry: " + str(laundry_count))
        
        # Case Management
        case_management_count = 0
        for item in case_management_item_codes:
            index = row_items.find(item)
            if index >= 0:
                string_list = row_items.split(item, 1)
                substring = string_list[1]

                i = substring.index(':')
                if substring[i+2].isdigit():
                    case_management_count += int(substring[i+2])
            if case_management_count > 0:
                items_string = (items_string + "Case Management: " + str(case_management_count) + "\n")
                items_dict['Case Management'] = case_management_count
            if self.show_output:
                print("Case Management: " + str(clothing_count))

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
                if substring[i+2].isdigit():
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
                string_list = row_items.split(item, maxsplit=1)
                substring = string_list[1]

                # get first ':' following item code
                i = substring.index(':')
                if substring[i+2].isdigit():
                    if item == "hygiene bag":
                        grooming_count += int(substring[i+2])*10
                    else:
                        grooming_count += int(substring[i+2])
        # add body wash + shampoo for each shower
        if shower_count > 0:
            grooming_count += (shower_count * 2)
        if grooming_count > 0:
            items_string = (items_string + "Grooming: " + str(grooming_count) + "\n")
            items_dict['Grooming'] = grooming_count
        if self.show_output:
            print("Grooming: " + str(grooming_count))

        # Laundry Products
        laundry_product_count = 0
        if laundry_count > 0:
            # add detergent for each laundry run (wash + dry)
            laundry_product_count += int(laundry_count / 2)
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
                if substring[i+2].isdigit():
                    if item == "snack bag":
                        food_count += int(substring[i+2])*4
                    else:
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
                if substring[i+2].isdigit():
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
                if substring[i+2].isdigit():
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
                if substring[i+2].isdigit():
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
                if substring[i+2].isdigit():
                    petgoods_count += int(substring[i+2])
        if petgoods_count > 0:
            items_string = (items_string + "Pet Goods: " + str(petgoods_count) + "\n")
            items_dict['Pet Goods'] = petgoods_count
        if self.show_output: 
            print("Pet Goods: " + str(petgoods_count))

        # Lounge Access
        lounge_access_count = 0
        for item in lounge_access_item_codes:
            index = row_items.find(item)
            if index >= 0:
                string_list = row_items.split(item)
                substring = string_list[1]

                i = substring.index(':')
                if substring[i+2].isdigit():
                    lounge_access_count += int(substring[i+2])
            if lounge_access_count > 0:
                items_string = (items_string + "Lounge Access: " + str(lounge_access_count) + "\n")
                items_dict['Lounge Access'] = lounge_access_count
            if self.show_output:
                print("Lounge Access: " + str(lounge_access_count))

        # Information
        information_count = 0
        for item in information_item_codes:
            index = row_items.find(item)
            if index >= 0:
                string_list = row_items.split(item)
                substring = string_list[1]

                i = substring.index(':')
                if substring[i+2].isdigit():
                    information_count += int(substring[i+2])
            if information_count > 0:
                items_string = (items_string + "Information: " + str(information_count) + "\n")
                items_dict['Information'] = information_count
            if self.show_output:
                print("Information: " + str(information_count))
        
        # Device Charging
        device_charging_count = 0
        for item in device_charging_item_codes:
            index = row_items.find(item)
            if index >= 0:
                string_list = row_items.split(item)
                substring = string_list[1]

                i = substring.index(':')
                if substring[i+2].isdigit():
                    device_charging_count += int(substring[i+2])
            if device_charging_count > 0:
                items_string = (items_string + "Device Charging: " + str(device_charging_count) + "\n")
                items_dict['Device Charging'] = device_charging_count
            if self.show_output:
                print("Device Charging: " + str(device_charging_count))

        # Transportation
        transportation_count = 0
        for item in transportation_item_codes:
            index = row_items.find(item)
            if index >= 0:
                string_list = row_items.split(item)
                substring = string_list[1]

                i = substring.index(':')
                if substring[i+2].isdigit():
                    transportation_count += int(substring[i+2])
            if transportation_count > 0:
                items_string = (items_string + "Transportation: " + str(transportation_count) + "\n")
                items_dict['Transportation'] = transportation_count
            if self.show_output:
                print("Transportation: " + str(transportation_count))
        
        # Healthcare
        healthcare_count = 0
        for item in healthcare_item_codes:
            index = row_items.find(item)
            if index >= 0:
                string_list = row_items.split(item)
                substring = string_list[1]

                i = substring.index(':')
                if substring[i+2].isdigit():
                    healthcare_count += int(substring[i+2])
            if healthcare_count > 0:
                items_string = (items_string + "Healthcare Count: " + str(healthcare_count) + "\n")
                items_dict['Healthcare'] = healthcare_count
            if self.show_output:
                print("Healthcare: " + str(healthcare_count))

        # Storage
        storage_count = 0
        for item in storage_item_codes:
            index = row_items.find(item)
            if index >= 0:
                string_list = row_items.split(item)
                substring = string_list[1]
                i = substring.index(':')
                if substring[i+2].isdigit():
                    storage_count += int(substring[i+2])
            if storage_count > 0:
                items_string = (items_string + "Storage Count: " + str(storage_count) + "\n")
                items_dict['Storage'] = storage_count
            if self.show_output:
                print("Storage: " + str(storage_count))

        # Street Outreach
        if location in ["BIT", "SEM", "ORL", "APO"]:
            street_outreach_count = 1 # every interaction counts for one street outreach
        else:
            street_outreach_count = 0
        for item in street_outreach_item_codes:
            index = row_items.find(item)
            if index >= 0:
                string_list = row_items.split(item)
                substring = string_list[1]

                i = substring.index(':')
                if substring[i+2].isdigit():
                    street_outreach_count += int(substring[i+2])
            if street_outreach_count > 0:
                items_string = (items_string + "Street Outreach Count: " + str(street_outreach_count) + "\n")
                items_dict['Street Outreach'] = street_outreach_count
            if self.show_output:
                print("Street Outreach: " + str(street_outreach_count))

        return items_dict
    
    # Make dictionary string more readable
    def __clean_dictionary_string(self, string):
        rep = {"{" : "", "}" : "", ", " : "\n"}
        rep = dict((re.escape(k), v) for k, v in rep.items())
        pattern = re.compile("|".join(rep.keys()))
        return pattern.sub(lambda m: rep[re.escape(m.group(0))], string)
    
    # Expects to find substring in format MM-DD-YEAR; returns in format MM-DD-YEAR
    def __get_date_from_filename(self, filename): #TODO: subject to change
        if self.export_version == "corsalisapp" and "Failed_entries" not in filename:
            date_string = re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", filename)
            og_date = datetime.strptime(date_string[0], '%Y-%m-%d')
            reformat_date = og_date.strftime('%m-%d-%Y')
            date = datetime.strptime(reformat_date, '%m-%d-%Y')
        else:
            date_string = re.search("([0-9]{2}\-[0-9]{2}\-[0-9]{4})", filename)
            date = datetime.strptime(date_string[0], '%m-%d-%Y')
        return date

    # Export cleaned and readable spreadsheet for data to be entered manually
    def __export_manual_entry_data(self):
        # get date from original file and output into new excel sheet
        date = self.__get_date_from_filename(self.filename)
        output_name = "ALLSALT" + " - " + str(date.strftime('%d')) + ' ' + str(date.strftime('%b')) + ' ' + str(date.strftime('%Y'))

        self.df.to_excel(self.output_path + output_name + ".xlsx", sheet_name=output_name)

    # Export a sheet of the failed automated entries in their original format
    # This way we can keep looping the failed entries and try again
    def __export_failed_automation_data(self):
        # get date from original file and output into new xlsx sheet
        date = self.__get_date_from_filename(self.filename)
        output_name = ("ALLSALT" + "_Failed_entries_" 
                       + str(date.strftime('%m')) + '-' 
                       + str(date.strftime('%d')) + '-' 
                       + str(date.strftime('%Y')))

        self.failed_df.to_excel(self.output_path + output_name + ".xlsx", sheet_name = "Failed Entries Report - " + output_name)
        print("Successfully updated failed entry report")