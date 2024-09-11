from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
import difflib
import time
import traceback

'''
Responsible for all automation, all the data should be processed and cleaned before
being sent to this class, i.e. by daily_data.py. All pandas and dataframe 
logic/manipulation should be done outside of this automation class.

I added the selectors to the top of each function in case they are subject to change
on HMIS' website. 
'''
class Driver:
    # Global Selectors
    iframe_id = "TabFrame_2"
    iframe_dialog_id = "Frame"
    iframe_dialog_counter = 1

    # Global Variables
    wait_time = 3

    '''
    ------------------------ SETUP ------------------------
    '''

    def __init__(self):
        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)

        # added for linux build
        chrome_options.add_argument("--headless")

        self.browser = Chrome(options=chrome_options)

    def open_clienttrack(self):
        self.browser.get('https://clienttrack.eccovia.com/login/HSNCFL')

    def login_clienttrack(self, username, password):
        field_username = self.browser.find_element(By.ID, "UserName")
        field_password = self.browser.find_element(By.ID, "Password")

        field_username.send_keys(username)
        field_password.send_keys(password)
        field_password.send_keys(Keys.RETURN)
        return True
    
    '''
    ------------------------ WORKFLOW ------------------------
    '''
    # Searches for a client by their ID number and checks that the name is a relative match once found
    # @param: [str] id: ID of the client being searched
    #         [str] first_name: first name to be checked
    #         [str] last_name: last name to be checked
    # @return: [bool] success / fail
    def search_client_by_ID(self, id, first_name, last_name):
        self.navigate_to_find_client()

        field_client_id_id = "1000005942_Renderer"
        button_search_id = "Renderer_SEARCH"
        label_client_name_xpath = '//td[@class="Header ZoneTopRow_2"]//a'

        # enter id into client id field
        self.__switch_to_iframe(self.iframe_id)
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, field_client_id_id))
            )
            field_client_id = self.browser.find_element(By.ID, field_client_id_id)        
            field_client_id.click()
            field_client_id.send_keys(id)

            button_search_id = self.browser.find_element(By.ID, button_search_id)
            button_search_id.click()
        except Exception as e:
            print("Couldn't find 'Client ID' field")
            print(traceback.format_exc())
            return False

        # check that name matches client data and id
        # should load directly to client dashboard
        self.__switch_to_iframe(self.iframe_id) # wait for new iframe to load

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.presence_of_element_located((By.XPATH, label_client_name_xpath))
            )
            dashboard_title = self.browser.find_element(By.XPATH, label_client_name_xpath).get_attribute("title")
            dashboard_name = dashboard_title.split("'s")[0]
            dashboard_first_name = dashboard_name.split(" ", 1)[0]
            dashboard_last_name = dashboard_name.split(" ", 1)[1]

            # calculate similarity score of the name on the dashboard and our clients name
            min_score = 0.80
            first_name_score = self.__similar(dashboard_first_name, first_name)
            last_name_score = self.__similar(dashboard_last_name, last_name) 
            final_score_one = first_name_score + last_name_score
            if final_score_one >= min_score:
                return True

            # sometimes first and last names are swapped, check both scenarios
            first_name_score = self.__similar(dashboard_first_name, last_name)
            last_name_score = self.__similar(dashboard_last_name, first_name) 
            final_score_two = first_name_score + last_name_score
            if final_score_two >= min_score:
                return True

            print("Client Name is not a match")
            print("Similarity Score:", max(final_score_one, final_score_two))
            print("Current Client: " + first_name, last_name)
            print("Loaded Client: " + dashboard_first_name, dashboard_last_name)
            return False
        except Exception as e:
            print("Couldn't find correct Client Name")
            return False

    # Searches for a client by their birthday and parses through the list of results,
    #   selecting the best match
    # @param: [str] birthdate: birthdate of the client being searched
    #         [str] first_name: first name to be checked
    #         [str] last_name: last name to be checked
    # @return: [bool] success / fail
    def search_client_by_birthdate(self, birthdate, first_name, last_name):
        self.navigate_to_find_client()

        field_birthdate_id = "1000005939_Renderer"
        button_search_id = "Renderer_SEARCH"
        table_search_results_rows_xpath = "//table[@id='RendererResultSet']//tbody/tr"

        self.__switch_to_iframe(self.iframe_id)
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, field_birthdate_id))
            )
            # enter birthday to field
            field_birthdate = self.browser.find_element(By.ID, field_birthdate_id)        
            field_birthdate.click()
            field_birthdate.send_keys(birthdate)

            button_search_id = self.browser.find_element(By.ID, button_search_id)
            button_search_id.click()
        except Exception as e:
            print("Couldn't find 'Birth Date' field")
            print(traceback.format_exc())
            return False

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.visibility_of_all_elements_located((By.XPATH, table_search_results_rows_xpath))
            )
            # search through rows in tables for best match
            result_max_score = 0
            table_search_results = self.browser.find_elements(By.XPATH, table_search_results_rows_xpath)
            for result in table_search_results:
                result_first_name = result.find_element(By.XPATH, "td[2]").text
                result_last_name = result.find_element(By.XPATH, "td[3]").text

                # calculate the similarity score of the current result in list
                first_name_score = self.__similar(result_first_name, first_name)
                last_name_score = self.__similar(result_last_name, last_name) 
                final_score = first_name_score + last_name_score
                min_score = 1.4

                # if a decent match, store the value and compare with other viable matches
                if final_score >= min_score:
                    if first_name_score + last_name_score > result_max_score:
                        # update new max value
                        result_max_score = first_name_score + last_name_score
                        stored_result = result

                # sometimes the first and last names are flipped
                first_name_score = self.__similar(result_first_name, last_name)
                last_name_score = self.__similar(result_last_name, first_name)
                final_score = first_name_score + last_name_score
                if final_score >= min_score:
                    if first_name_score + last_name_score > result_max_score:
                        # update new max value
                        result_max_score = first_name_score + last_name_score
                        stored_result = result
            # For Loop End
                
            if result_max_score > 0:
                stored_result.click()
                return True

            # if there still isn't a decent match, check middle name field and different combinations
            print("Checking Middle Name")
            last_names = last_name.split(" ", 1) 
            names = last_names + [first_name]

            for result in table_search_results:
                result_first_name = result.find_element(By.XPATH, "td[2]").text
                result_last_name = result.find_element(By.XPATH, "td[3]").text
                result_mid_name = result.find_element(By.XPATH, "td[4]").text
                # if client has two names i.e. James Yates
                if len(names) <= 2:
                    min_score = 1.4
                    mid_name_score = max(self.__similar(first_name, result_mid_name),
                                          self.__similar(last_name, result_mid_name))
                    first_name_score = max(self.__similar(first_name, result_first_name),
                                           self.__similar(last_name, result_first_name))
                    last_name_score = max(self.__similar(first_name, result_last_name),
                                          self.__similar(last_name, result_last_name))
                    final_score = max((first_name_score + mid_name_score), (last_name_score + mid_name_score))
                    if final_score >= min_score and final_score > result_max_score:
                        result_max_score = final_score
                        stored_result = result
                # if client name has three names i.e. James Baxton Yates, check every combo
                else:
                    min_score = 2 # 3 is a perfect match (first, middle, last)
                    # check every combination of names to middle names
                    for name in names:
                        remaining_names = names.copy()
                        remaining_names.remove(name)

                        first_name_score = self.__similar(result_first_name, name)
                        for i in range(2):
                            mid_name_score = self.__similar(result_mid_name, remaining_names[i%2])
                            last_name_score = self.__similar(result_last_name, remaining_names[(i+1)%2])
                            final_score = first_name_score + mid_name_score + last_name_score
                            if final_score >= min_score and final_score > result_max_score:
                                result_max_score = final_score
                                stored_result = result
            # For Loop End

            if result_max_score > 0:
                stored_result.click()
                return True

            print("Couldn't find client name among results")
            return False
        except Exception as e:
            print("Error finding list of results")
            print(traceback.format_exc())
            return False

    # Enters the services for the current client that's loaded
    # @param: [list] viable_enrollment_list: list of favorable SALT enrollments, ordered from
    #                                        most to least favorable
    #         [str] service_date: date of service
    #         [dict] services_dict: dictionary of services to be entered
    # @return: [bool] success / fail
    def enter_client_services(self, viable_enrollment_list, service_date, services_dict, location):
        button_add_new_service_id = "Renderer_1000000216"
        dropdown_enrollment_id = "1000007089_Renderer"
        dropdown_service_id = "1000007094_Renderer"

        # the corresponding values that serve as different service codes
        # these keys should line up with the ones in service_dict
        options_service_values = {'Bible Study' : '690',
                                  'Shower' : '289',
                                  'Laundry' : '529',
                                  'Laundry Products' : '605',
                                  'Bedding' : '538',
                                  'Clothing' : '526',
                                  'Grooming' : '530',
                                  'Food' : '359',
                                  'Case Management': '372'}
        
        field_units_id = "1000007095_Renderer"
        field_date_id = "1000007086_Renderer"
        button_save_id = "Renderer_SAVE"

        # update date of engagement and enroll client if not already enrolled
        # if fails, do nothing; automation will enroll them anyway when entering services
        # and thus keep the date of engagement updated
        # for now only street outreach can update date of engagement
        # DoE_enrollment_list = [x for x in viable_enrollment_list if 'Street' in x]
        # if not self.update_date_of_engagement(DoE_enrollment_list, service_date):
        #     print("Couldn't update date of engagement")
        # else:
        #     self.__wait_until_page_fully_loaded('Enrollment')
        #     self.__wait_until_result_set_fully_loaded()

        self.navigate_to_client_dashboard()
        self.navigate_to_service_list()

        # start entering services
        for service, service_count in services_dict.items():
            # wait until 'Services' page is fully loaded and 'Add Service Button' is clickable
            self.__switch_to_iframe(self.iframe_id)
            self.__wait_until_page_fully_loaded('Service')
            self.__wait_until_result_set_fully_loaded()
            try:
                WebDriverWait(self.browser, self.wait_time).until(
                    EC.element_to_be_clickable((By.ID, button_add_new_service_id))
                )
                button_add_new_service = self.browser.find_element(By.ID, button_add_new_service_id)
                button_add_new_service.click()
            except Exception as e:
                print("Couldn't click 'Add New Service' button")
                print(traceback.format_exc())
                return False
            
            # wait for 'Add Service' page to be fully loaded
            self.__wait_until_page_fully_loaded('Add Service')

            # find viable 'enrollment' option in the drop down list
            try:
                WebDriverWait(self.browser, self.wait_time).until(
                    EC.element_to_be_clickable((By.ID, dropdown_enrollment_id))
                )
                dropdown_enrollment = self.browser.find_element(By.ID, dropdown_enrollment_id)
                dropdown_options = dropdown_enrollment.find_elements(By.TAG_NAME, 'option')

                enrollment_found = False
                for salt_enrollment in viable_enrollment_list:
                    if not enrollment_found:
                        for option in dropdown_options:
                            if salt_enrollment in option.text:
                                option.click()
                                enrollment_found = True
                                break
                # enroll the client and try again, enrollment should be found in recursive call
                if not enrollment_found:
                    '''
                    print("Client is not enrolled")
                    return False
                    '''
                    print("Client is not enrolled -- Enrolling client")
                    self.navigate_to_client_dashboard()
                    if not self.enroll_client(service_date, location):
                        print("Couldn't enroll client successfully -- Canceling")
                        self.__cancel_intake_workflow()
                        self.__wait_until_page_fully_loaded("Client Dashboard")
                        self.navigate_to_find_client()
                        return False

                    print("Successfully enrolled client -- Entering services")
                    return self.enter_client_services(viable_enrollment_list, service_date, services_dict, location)
            except Exception as e:
                print("Error finding enrollment")
                print(traceback.format_exc())
                return False

            try:
                # enter corresponding service - added sleep, as filling the form too fast causes it to be incorrect
                service_code = options_service_values[service]
                dropdown_option_xpath = '//select[@id="%s"]//option[@value="%s"]' %(dropdown_service_id, service_code)
                option_service = self.browser.find_element(By.XPATH, dropdown_option_xpath)
                option_service.click()
                time.sleep(1)
            
                # enter unit value
                field_units = self.browser.find_element(By.ID, field_units_id)
                field_units.clear()
                time.sleep(1)
                field_units.send_keys(service_count)
                time.sleep(1)

                # enter date
                field_date = self.browser.find_element(By.ID, field_date_id)
                field_date.clear()
                field_date.send_keys(service_date)
                time.sleep(1)

                # click save button
                button_save = self.browser.find_element(By.ID, button_save_id)
                button_save.click()
                time.sleep(2)
            except Exception as e:
                print("Couldn't enter " + service + " service for client")
                print(traceback.format_exc())
                return False
        # For Loop End - Success!
        return True
    
    # Enrolls the client into the latest SALT program
    # @param: [str] service_date: date of service
    # @return: [bool] success / fail
    def enroll_client(self, service_date, location):
        button_new_enrollment_id = "Renderer_1000000424"
        dropdown_veteran_status_id = "1000006680_Renderer"
        option_data_not_collected_value = "99"
        button_finish_id = "Renderer_SAVE"
        button_save_and_close_id = "Renderer_SAVEFINISH"
        dropdown_project_id = "1000004260_Renderer"
        dropdown_rel_to_head_of_household_xpath = '//table[@id="RendererSF1ResultSet"]//tr/td/select'
        field_project_date_xpath = '//table[@id="RendererSF1ResultSet"]//tr/td/span[@class="DateField input-group"]/input'
        field_date_of_engagement_xpath = '//table[@id="RendererSF1ResultSet"]//tr/td/span[@class="DateField input-group"]/input'
        button_save_id = "Renderer_SAVE"
        table_row_family_members_xpath = '//table[@id="RendererSF1ResultSet"]//tbody/tr'

        # 1217 for downtown, 1157 for sanford
        option_salt_enrollment_value = "1217" if location == "ORL" else "1157"

        self.navigate_to_enrollment_list()

        # wait for Enrollments page to be fully loaded before clicking new enrollment button
        self.__switch_to_iframe(self.iframe_id)
        self.__wait_until_page_fully_loaded('Enrollments')
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, button_new_enrollment_id))
            )
            button_new_enrollment = self.browser.find_element(By.ID, button_new_enrollment_id)
            button_new_enrollment.click()
        except Exception as e:
            print("Couldn't click 'New Enrollment' button")
            print(traceback.format_exc())
            return False
        
        # wait for Intake page to be fully loaded
        self.__wait_until_page_fully_loaded('Intake - Basic Client Info')

        # sometimes the 'Veteran Status' field hasn't been updated as its a new required field
        # check that the dropdown isn't on "--SELECT--" option before hitting submit
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, dropdown_veteran_status_id))
            )
            dropdown_veteran_status = Select(self.browser.find_element(By.ID, dropdown_veteran_status_id))
            selected_option = dropdown_veteran_status.first_selected_option

            if "SELECT" in selected_option.text:
                option_data_not_collected_xpath = ('//select[@id="%s"]//option[@value="%s"]' 
                                                   %(dropdown_veteran_status_id, option_data_not_collected_value))
                option_data_not_collected = self.browser.find_element(By.XPATH, option_data_not_collected_xpath)
                option_data_not_collected.click()
            time.sleep(1)
        except Exception as e:
            print("Couldn't update Veteran Status, field not selected (sometimes doesn't exist)")
            # print(traceback.format_exc())
            # Don't return an error and quit, sometimes this field doesn't exist

        button_finish = self.browser.find_element(By.ID, button_finish_id)
        button_finish.click()
        time.sleep(2)

        # wait until 'Family Members' section loads
        self.__switch_to_iframe(self.iframe_id)
        self.__wait_until_page_fully_loaded('Intake - Family Members')

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, button_save_and_close_id))
            )
            button_save_and_close = self.browser.find_element(By.ID, button_save_and_close_id)
            button_save_and_close.click()
        except Exception as e:
            print("Couldn't Save 'Family Members' section of Intake")
            print(traceback.format_exc())
            return False

        # wait until 'Program Enrollment' section loads
        self.__switch_to_iframe(self.iframe_id)
        self.__wait_until_page_fully_loaded('Intake - Program Enrollment')
        
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, dropdown_project_id))
            )
            dropdown_option_xpath = '//select[@id="%s"]//option[@value="%s"]' %(dropdown_project_id, option_salt_enrollment_value)
            option_salt_orl = self.browser.find_element(By.XPATH, dropdown_option_xpath)
            option_salt_orl.click()
            time.sleep(1)
        except Exception as e:
            print("Couldn't find SALT ORL Enrollment in options")
            print(traceback.format_exc())
            return False

        # update household data for program enrollment and only enroll current client (not family members)
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.presence_of_element_located((By.XPATH, dropdown_rel_to_head_of_household_xpath))
            )
            # if the household has multiple members, look for the current client to enroll
            rows_family_members = self.browser.find_elements(By.XPATH, table_row_family_members_xpath)

            if len(rows_family_members) < 2:
                field_project_date = self.browser.find_elements(By.XPATH, field_project_date_xpath)[2]
                field_date_of_engagement = self.browser.find_elements(By.XPATH, field_date_of_engagement_xpath)[4]
            else:
                self.browser.switch_to.default_content()
                label_client_name_xpath = '//span[@aria-label="Name"]'
                str = self.browser.find_element(By.XPATH, label_client_name_xpath).text
                client_name = str.split(' ')[1] + ", " + str.split(' ')[0]
                self.__switch_to_iframe(self.iframe_id)

                stored_row = rows_family_members[0]
                max_score = 0
                for row in rows_family_members:
                    row_name = row.find_element(By.XPATH, "./th").text
                    score = self.__similar(row_name, client_name)
                    if score > max_score:
                        stored_row = row
                        max_score = score

                option_self = stored_row.find_element(By.XPATH, './/select//option[@value="SL"]')
                time.sleep(1)
                self.browser.execute_script("arguments[0].scrollIntoView({block: 'end'});", stored_row.find_element(By.XPATH,'.//select'))
                time.sleep(1)
                option_self.click()

                field_project_date = stored_row.find_elements(By.XPATH, './td/span[@class="DateField input-group"]/input')[2]
                field_date_of_engagement = stored_row.find_elements(By.XPATH, './td/span[@class="DateField input-group"]/input')[4]

            time.sleep(2)
            self.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", field_project_date)
            time.sleep(2)
            WebDriverWait(self.browser, self.wait_time).until(EC.element_to_be_clickable(field_project_date))
            field_project_date.click()
            time.sleep(1)
            field_project_date.clear()
            time.sleep(3)
            self.browser.execute_script("arguments[0].scrollIntoView();", field_project_date)
            time.sleep(1)
            field_project_date.send_keys(service_date)
            time.sleep(1)


            '''
            # No longer updating date of engagement
            self.browser.execute_script("arguments[0].scrollIntoView();", field_date_of_engagement)
            time.sleep(1)
            WebDriverWait(self.browser, self.wait_time).until(EC.element_to_be_clickable(field_date_of_engagement))
            field_date_of_engagement.click()
            time.sleep(1)
            field_date_of_engagement.clear()
            time.sleep(1)
            field_date_of_engagement.send_keys(service_date)
            time.sleep(1)
            '''

            button_save = self.browser.find_element(By.ID, button_save_id)
            button_save.click()
            time.sleep(1)
        except Exception as e:
            print("Couldn't update household")
            print(traceback.format_exc())
            return False

        # Assess Client
        return self.__assess_client(service_date, location)
        
    def __assess_client(self, service_date, location):
        dropdowns_xpath = '//table[@class="FormPage"]//td[@class="FieldStyle"]/select'
        date_fields_xpath = '//table[@class="FormPage"]//td[@class="FieldStyle"]/span[@class="DateField input-group"]/input'
        option_data_not_collected_id = '99'
        option_no_id = '0'
        option_orange_county_id = '1'
        option_sem_county_id = '2'
        option_place_not_meant_for_habitation_id = '16'
        button_save_id = 'Renderer_SAVE'
        button_default_assessment_id = 'B1000006792_Renderer'


        self.__default_last_assessment(button_default_assessment_id)
        self.__wait_until_page_fully_loaded('Universal Data Assessment')

        # INITIAL ASSESSMENT
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.visibility_of_any_elements_located((By.XPATH, date_fields_xpath))
            )

            # Client Information
            field_assessment_date_id = '1000006788_Renderer'
            field_assessment_date = self.browser.find_element(By.ID, field_assessment_date_id)
            field_assessment_date.click()
            field_assessment_date.clear()
            field_assessment_date.send_keys(service_date)

            dropdown_disabling_condition_id = '1000006806_Renderer'
            dropdown_disabling_condition = self.browser.find_element(By.ID, dropdown_disabling_condition_id)
            if self.__dropdown_empty(dropdown_disabling_condition):
                self.__select_assessment_dropdown_option(dropdown_disabling_condition, option_no_id)

            # Enrollment CoC
            dropdown_county_id = '1000006849_Renderer'
            dropdown_county = self.browser.find_element(By.ID, dropdown_county_id)
            if self.__dropdown_empty(dropdown_county):
                option_county_id = option_orange_county_id if location == 'ORL' else option_sem_county_id
                self.__select_assessment_dropdown_option(dropdown_county, option_county_id)

            # Living Situation
            dropdown_prior_living_sit_id = '1000006811_Renderer'
            dropdown_prior_living_sit = self.browser.find_element(By.ID, dropdown_prior_living_sit_id)
            if self.__dropdown_empty(dropdown_prior_living_sit):
                self.__select_assessment_dropdown_option(dropdown_prior_living_sit, option_place_not_meant_for_habitation_id)

            dropdown_length_of_stay_id = '1000006812_Renderer'
            dropdown_length_of_stay = self.browser.find_element(By.ID, dropdown_length_of_stay_id)
            if self.__dropdown_empty(dropdown_length_of_stay):
                self.__select_assessment_dropdown_option(dropdown_length_of_stay, option_data_not_collected_id)

            field_homeless_start_date_id = '1000006795_Renderer'
            field_homeless_start_date = self.browser.find_element(By.ID,field_homeless_start_date_id)
            field_value = field_assessment_date.get_property("value")
            str = field_value.replace("/", "")
            # if its the date of service, it means the field is empty
            if service_date in str:
                field_homeless_start_date.click()
                time.sleep(1)
                field_homeless_start_date.clear()
                time.sleep(1)
                field_homeless_start_date.send_keys(service_date)
                time.sleep(1)
            
            dropdown_street_frequency_id = '1000006807_Renderer'
            dropdown_street_frequency = self.browser.find_element(By.ID, dropdown_street_frequency_id)
            if self.__dropdown_empty(dropdown_street_frequency):
                self.__select_assessment_dropdown_option(dropdown_street_frequency, option_data_not_collected_id)

            dropdown_months_homeless_id = '1000006813_Renderer'
            dropdown_months_homeless = self.browser.find_element(By.ID, dropdown_months_homeless_id)
            if self.__dropdown_empty(dropdown_months_homeless):
                self.__select_assessment_dropdown_option(dropdown_months_homeless, option_data_not_collected_id)

            # Insurance Status
            button_default_assessment_id = 'B1000006761_Renderer'
            self.__default_last_assessment(button_default_assessment_id)
            self.__wait_until_page_fully_loaded('Universal Data Assessment')

            dropdown_covered_by_health_ins_id = '1000006802_Renderer'
            dropdown_covered_by_health_ins = self.browser.find_element(By.ID, dropdown_covered_by_health_ins_id)
            if self.__dropdown_empty(dropdown_covered_by_health_ins):
                self.__select_assessment_dropdown_option(dropdown_covered_by_health_ins, option_data_not_collected_id)

            # Save
            button_save = self.browser.find_element(By.ID, button_save_id)
            button_save.click()
            time.sleep(1)
        except Exception as e:
            print("Couldn't complete initial assessment")
            print(traceback.format_exc())
            return False

        # BARRIER ASSESSMENT
        button_default_assessment_id = 'B1000006792_Renderer'
        field_identified_date_id = '90688_Renderer'
        button_save_and_close_id = 'Renderer_SAVEFINISH'

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, field_identified_date_id))
            )

            # sometimes this button isn't available
            button_default_assessment = self.browser.find_elements(By.ID, button_default_assessment_id)
            already_assessed = False
            if len(button_default_assessment) > 1:
                already_assessed = True
                button_default_assessment[0].click()
                time.sleep(3)

            dropdowns_xpath = '//table[@id="RendererResultSet"]//tr/td/select[@class="form-control"]'
            dropdowns = self.browser.find_elements(By.XPATH, dropdowns_xpath)

            # every fouth dropdown is a 'Barrier Present?' field
            for i in range(0, len(dropdowns), 4):
                if self.__dropdown_empty(dropdowns[i]):
                    self.__select_assessment_dropdown_option(dropdowns[i], option_data_not_collected_id)

            # Save
            button_save_and_close = self.browser.find_element(By.ID, button_save_and_close_id)
            button_save_and_close.click()
            time.sleep(2) 

            # depending on the case, it might have to click save and close twice
            if already_assessed and self.browser.find_elements(By.ID, button_save_and_close_id) > 1:
                button_save_and_close = self.browser.find_element(By.ID, button_save_and_close_id)
                button_save_and_close.click()
                time.sleep(2) 

        except Exception as e:
            print("Couldn't complete barrier assessment")
            print(traceback.format_exc())
            return False

        # DOMESTIC VIOLENCE ASSESSMENT
        button_default_assessment_id = 'B48899_Renderer'
        field_assessment_date_id = '11807_Renderer'
        button_save_id = "Renderer_SAVE"

        self.__default_last_assessment(button_default_assessment_id)
        self.__wait_until_page_fully_loaded("Domestic Violence Assessment")

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, field_assessment_date_id))
            )
            
            buttons_domestic_violence_xpath = '//span[@id="11888_Renderer"]//input[@type="radio"]'
            buttons_domestic_violence = self.browser.find_elements(By.XPATH, buttons_domestic_violence_xpath)
            is_empty = True
            for button in buttons_domestic_violence:
                if button.is_selected():
                    is_empty = False
            if is_empty:
                buttons_domestic_violence[4].click()
                time.sleep(1)

            # Save
            button_save = self.browser.find_element(By.ID, button_save_id)
            button_save.click()
            time.sleep(1)
        except Exception as e:
            print("Couldn't complete domestic violence assessment")
            print(traceback.format_exc())
            return False

        # INCOME ASSESSMENT
        field_assessment_date_id = '92172_Renderer'
        dropdown_income_id = '92173_Renderer'
        dropdown_non_cash_benefits_id = '92174_Renderer'
        button_save_id = "Renderer_SAVE"
        button_default_assessment_id = 'B92169_Renderer'

        self.__default_last_assessment(button_default_assessment_id)
        self.__wait_until_page_fully_loaded("Income Assessment")
        # FIX HERE, HANGING TODO

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, field_assessment_date_id))
            )
            dropdown_income = self.browser.find_element(By.ID, dropdown_income_id)
            if self.__dropdown_empty(dropdown_income):
                self.__select_assessment_dropdown_option(dropdown_income, option_data_not_collected_id)

            dropdown_cash_benefits = self.browser.find_element(By.ID, dropdown_non_cash_benefits_id)
            if self.__dropdown_empty(dropdown_cash_benefits):
                self.__select_assessment_dropdown_option(dropdown_cash_benefits, option_data_not_collected_id)

            # Save
            button_save = self.browser.find_element(By.ID, button_save_id)
            button_save.click()
            time.sleep(1)
        except Exception as e:
            print("Couldn't complete income assessment")
            print(traceback.format_exc())
            return False

        # CURRENT LIVING SITUATION ASSESSMENT
        self.__wait_until_page_fully_loaded("Current Living Situation Assessment")

        dropdown_living_sit_id = '107051_Renderer'
        button_save_id = "Renderer_SAVE"

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, dropdown_living_sit_id))
            )
            dropdown_living_sit = self.browser.find_element(By.ID, dropdown_living_sit_id)
            self.__select_assessment_dropdown_option(dropdown_living_sit, option_place_not_meant_for_habitation_id)

            # Save
            button_save = self.browser.find_element(By.ID, button_save_id)
            button_save.click()
            time.sleep(1)
        except Exception as e:
            print("Couldn't complete current living situation assessment")
            print(traceback.format_exc())
            return False

        # TRANSLATION ASSISTANCE ASSESSMENT
        dropdown_translation_id = '107564_Renderer'
        button_save_id = "Renderer_SAVE"
        button_default_assessment_id = 'B107569_Renderer'

        self.__default_last_assessment(button_default_assessment_id)
        self.__wait_until_page_fully_loaded("Translation Assistance Assessment")

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, dropdown_translation_id))
            )
            dropdown_translation = self.browser.find_element(By.ID, dropdown_translation_id)
            if self.__dropdown_empty(dropdown_translation):
                self.__select_assessment_dropdown_option(dropdown_translation, option_data_not_collected_id)

            # Save
            button_save = self.browser.find_element(By.ID, button_save_id)
            button_save.click()
            time.sleep(1)
        except Exception as e:
            print("Couldn't complete translation assistance assessment")
            print(traceback.format_exc())
            return False

        # FINISH BUTTON
        self.__wait_until_page_fully_loaded("Finish Page")
        button_finish_id = 'FinishButton'

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, button_finish_id))
            )
            button_finish = self.browser.find_element(By.ID, button_finish_id)
            button_finish.click()
            time.sleep(1)
        except Exception as e:
            print("Couldn't click the finish enrollment button")
            print(traceback.format_exc())
            return False
        
        # SUCCESS
        return True

    def __dropdown_empty(self, dropdown):
        selected_option = Select(dropdown).first_selected_option.text
        return True if "SELECT" in selected_option else False
    
    # might only work on assessment page
    def __select_assessment_dropdown_option(self, dropdown, option_id):
        dropdown_id = dropdown.get_attribute("id")
        dropdown_option_xpath = '//select[@id="%s"]//option[@value="%s"]' %(dropdown_id, option_id)
        option = self.browser.find_element(By.XPATH, dropdown_option_xpath)
        option.click()
        time.sleep(1)

    def __default_last_assessment(self, button_default_assessment_id):
        # click default last assessment button and wait for page to load
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, button_default_assessment_id))
            )
            button_default_assessment = self.browser.find_element(By.ID, button_default_assessment_id)
            button_default_assessment.click()
            time.sleep(3)
        except Exception as e:
            # sometimes this button doesn't exist, just skip over
            print("Couldn't click last assessment button")
    
    # Mimics logic of 'update_date_of_engagement', 'navigate_to_edit_enrollment' and 'open_link_in_enrollment_action_menu'
    #   for special case scenario: deleting date of engagement fields that are supposed to be empty, but 
    #   are not. Developed to fix an error pointed out by the HMIS team in our data
    # @return: [bool] success / fail
    def delete_date_of_engagement(self):
        label_enrollment_row_name_xpath = ('//table[@id="wp85039573formResultSet"]/tbody//td[6]')
        links_enrollment_action_ids = {'Edit Enrollment': 'amb3',
                                       'Edit Project Entry Workflow': 'amb4'}
        menu_id = 'ActionMenu'
        link_id = links_enrollment_action_ids['Edit Enrollment']

        field_date_of_engagement_xpath = '//table[@id="RendererSF1ResultSet"]/tbody/tr/td/span/input'
        field_assessment_xpath = '//table[@class="FormPage"]//td/span/input'
        table_row_family_members_xpath = '//table[@id="RendererSF1ResultSet"]//tbody/tr'
        button_save_id = "Renderer_SAVE"

        self.__switch_to_iframe(self.iframe_id)
        self.__wait_until_page_fully_loaded('Client Dashboard')


        # STEP ONE: NAVIGATE TO EDIT ENROLLMENT PAGE
        # check if client is enrolled in two SALT programs, if so skip over client and return true
        # else click on the enrollment and open the row's action menu
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.visibility_of_element_located((By.XPATH, label_enrollment_row_name_xpath))
            )
            rows_enrollment_xpath = '//table[@id="wp85039573formResultSet"]/tbody/tr'
            rows_enrollment = self.browser.find_elements(By.XPATH, rows_enrollment_xpath)
            stored_row = None

            for row in rows_enrollment:
                # if row is a header (i.e. Active, Exited)
                if row.get_attribute("class") == "gbHead":
                    # prevent from clicking on an expired enrollment
                    label = row.find_element(By.XPATH, './td/a')
                    if label.get_attribute("data-value") == "Exited":
                        break
                # if row contains enrollment data
                else:
                    label_enrollment_name = row.find_element(By.XPATH, './td[6]').text
                    if 'SALT' in label_enrollment_name:
                        if stored_row:
                            print("Enrolled in multiple SALT projects")
                            return True # skip over current client and return success
                        stored_row = row
            # For Loop End

            # no valid SALT enrollments, has probably been exited from a program
            if stored_row == None:
                print("No valid SALT enrollment exists for client")
                return True

            menu_action = stored_row.find_element(By.CLASS_NAME, 'action-menu')
            self.browser.execute_script("arguments[0].scrollIntoView();", menu_action)
            time.sleep(1)
            menu_action.click()

        except Exception as e:
            print("Couldn't open Enrollment Action Menu")
            print(traceback.format_exc())
            return False

        # wait for action menu to appear
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.visibility_of_element_located((By.ID, menu_id))
            )
        except Exception as e:
            print("Couldn't find Action Menu")
            print(traceback.format_exc())
            return False

        # select the 'edit enrollment' link option from the action menu
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, link_id))
            )
            link = self.browser.find_element(By.ID, link_id)
            link.click()
        except Exception as e:
            print("Couldn't click link in Action Menu")
            print(traceback.format_exc())
            return False

        # STEP TWO: CLEAR DATE OF ENGAGEMENT FIELD 
        # wait for Edit Enrollment page to be fully loaded
        self.__switch_to_iframe(self.iframe_id)
        self.__wait_until_page_fully_loaded('Edit Enrollment')
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.visibility_of_any_elements_located((By.XPATH, field_date_of_engagement_xpath))
            )
        except:
            print("Error loading Edit Enrollment page")
            print(traceback.format_exc())
            return False

        try:
            # find our current client among table of family members to update date of engagement
            rows_family_members = self.browser.find_elements(By.XPATH, table_row_family_members_xpath)
            for row in reversed(rows_family_members):
                select_rel_to_head_of_household = row.find_elements(By.XPATH, './td/select')[0]
                dropdown_rel_to_head_of_household = Select(select_rel_to_head_of_household)
                rel_to_head_of_household = dropdown_rel_to_head_of_household.first_selected_option.text
                if rel_to_head_of_household == "Self":
                    field_date_of_engagement = row.find_elements(By.XPATH, './td/span/input')[5]
                    WebDriverWait(self.browser, self.wait_time).until(EC.element_to_be_clickable(field_date_of_engagement))
                    time.sleep(1)
                    self.browser.execute_script("arguments[0].scrollIntoView();", field_date_of_engagement)
                    time.sleep(1)
                    field_date_of_engagement.click()
                    time.sleep(1)
                    field_date_of_engagement.clear()
                    time.sleep(1)
                    button_save = self.browser.find_element(By.ID, button_save_id)
                    button_save.click()
        except Exception as e:
            print("Date of Engagement field does not exist")
            return True # sometimes the field does not exist for the user, I'm not sure why
        return True

    # Updates the date of engagement field in the 'Edit Enrollment' page to be the date of service
    # @param: [list] viable_enrollment_list: list of favorable SALT enrollments, ordered from
    #                                        most to least favorable
    #         [str] service_date: date of service
    # @return: [bool] success / fail
    def update_date_of_engagement(self, viable_enrollment_list, service_date):
        table_row_family_members_xpath = '//table[@id="RendererSF1ResultSet"]//tbody/tr'
        field_date_of_engagement_xpath = '//table[@id="RendererSF1ResultSet"]/tbody/tr/td/span/input'
        field_assessment_xpath = '//table[@class="FormPage"]//td/span/input'
        button_save_id = "Renderer_SAVE"

        self.__switch_to_iframe(self.iframe_id)
        self.__wait_until_page_fully_loaded('Client Dashboard')

        # if isinstance(self.navigate_to_edit_enrollment, Exception):
        #   return False

        # if the enrollment hasn't been found, enroll the client
        # once enrolled, the date of engagement will already be updated
        if not self.navigate_to_edit_enrollment(viable_enrollment_list):
            return False

        # wait for Edit Enrollment page to be fully loaded
        self.__switch_to_iframe(self.iframe_id)
        self.__wait_until_page_fully_loaded('Edit Enrollment')

        # update Date of Engagement field
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.visibility_of_any_elements_located((By.XPATH, field_date_of_engagement_xpath))
            )
            # check if the client has had any assessments done (required for update)
            field_assessment = self.browser.find_elements(By.XPATH, field_assessment_xpath)[3]
            if not field_assessment.get_attribute("value"):
                return False
            # find our current client among table of family members to update date of engagement
            rows_family_members = self.browser.find_elements(By.XPATH, table_row_family_members_xpath)
            for row in reversed(rows_family_members):
                select_rel_to_head_of_household = row.find_elements(By.XPATH, './td/select')[0]
                dropdown_rel_to_head_of_household = Select(select_rel_to_head_of_household)
                rel_to_head_of_household = dropdown_rel_to_head_of_household.first_selected_option.text
                if rel_to_head_of_household == "Self":
                    field_date_of_engagement = row.find_elements(By.XPATH, './td/span/input')[5]
                    WebDriverWait(self.browser, self.wait_time).until(EC.element_to_be_clickable(field_date_of_engagement))
                    time.sleep(1)
                    self.browser.execute_script("arguments[0].scrollIntoView();", field_date_of_engagement)
                    time.sleep(1)
                    field_date_of_engagement.click()
                    time.sleep(1)
                    field_date_of_engagement.clear()
                    time.sleep(1)
                    field_date_of_engagement.send_keys(service_date)
                    time.sleep(1)
                    button_save = self.browser.find_element(By.ID, button_save_id)
                    button_save.click()
                    time.sleep(1)
        except Exception as e:
            print("Couldn't update Date of Engagement")
            print(traceback.format_exc())
            return False
        return True

    '''
    ------------------------ NAVIGATION ------------------------
    '''
    # This function can be accessed from any page in HMIS
    # @return: [bool] success / fail 
    def navigate_to_client_dashboard(self):
        button_nav_clients_page_id = "ws_2_tab"
        button_nav_dashboard_page_id = "o1000000033"

        # find 'Clients' button on left sidebar
        self.browser.switch_to.default_content()
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, button_nav_clients_page_id))
            )
            button_clients = self.browser.find_element(By.ID, button_nav_clients_page_id)
            button_clients.click()
        except Exception as e:
            print("Couldn't navigate to 'Clients' page")
            print(traceback.format_exc())
            return False

        # click 'Dashboard' button in sidebar
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, button_nav_dashboard_page_id))
            )
            button_dashboard = self.browser.find_element(By.ID, button_nav_dashboard_page_id)
            button_dashboard.click()
        except Exception as e:
            print("Couldn't navigate to 'Dashboard' page")
            print(traceback.format_exc())
            return False

    # This function can be accessed from any page in HMIS
    # @return: [bool] success / fail
    def navigate_to_find_client(self):
        button_nav_find_clients_page_id = "o1000000037"

        self.navigate_to_client_dashboard()
        
        # find 'Find Client' button on left sidebar after waiting for client dashboard to fully load
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, self.iframe_id))
            ) 
            self.browser.switch_to.default_content()
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, button_nav_find_clients_page_id))
            )
            button_find_client = self.browser.find_element(By.ID, button_nav_find_clients_page_id)
            button_find_client.click()
        except Exception as e:
            print("Couldn't open 'Find Client' page")
            print(traceback.format_exc())
            return False
        return True

    # IMPORTANT: This function can only work if the browser is navigating from the 'Client Dashboard' page
    #   Navigates to the list of services page for the current client loaded
    # @return: [bool] success / fail
    def navigate_to_service_list(self):
        link_services_xpath = '//td[@class="Header ZoneMiddleRight_2"]//a'

        self.__wait_until_page_fully_loaded("Client Dashboard")
        self.__switch_to_iframe(self.iframe_id)
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, link_services_xpath))
            )
            link_services = self.browser.find_element(By.XPATH, link_services_xpath)
            link_services.click()
        except Exception as e:
            print("Couldn't click 'Services' link")
            print(traceback.format_exc())
            return False
        return True
    
    # IMPORTANT: This function can only work if the browser is navigating from the 'Client Dashboard' page
    #   Navigates to a list of the enrollments for the current client loaded
    # @return: [bool] success / fail
    def navigate_to_enrollment_list(self):
        self.__wait_until_page_fully_loaded("Client Dashboard")
        link_enrollments_xpath = '//td[@class="Header ZoneMiddleMiddle_2"]//a'

        self.__switch_to_iframe(self.iframe_id)
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, link_enrollments_xpath))
            )
            link_enrollments = self.browser.find_element(By.XPATH, link_enrollments_xpath)
            link_enrollments.click()
        except Exception as e:
            print("Couldn't click 'Enrollments' link")
            print(traceback.format_exc())
            return False
        return True
    
    # IMPORTANT: This function can only work if the browser is navigating from the 'Client Dashboard' page
    #   Navigates to the edit enrollment page from the client's enrollment list on the dashboard
    # @param: [list] viable_enrollment_list: list of valid SALT enrollments that can be edited, ordered from most
    #                                        favorable to least
    # @return: [bool] success / fail
    def navigate_to_edit_enrollment(self, viable_enrollment_list):
        self.__wait_until_page_fully_loaded("Client Dashboard")
        self.__switch_to_iframe(self.iframe_id)

        return self.__open_link_in_enrollment_action_menu(viable_enrollment_list, "Edit Enrollment")

    # Finds a favorable enrollment under the list of enrollments on the 'Client Dashboard' page
    #   and clicks its action menu
    # @param: [list] viable_enrollment_list: list of valid SALT enrollments that can be edited, ordered from
    #                                 most favorable to least
    #         [str] link_name: name of the page to be opened from the Action Menu, should be one of the
    #                    options that are under the action menu
    # @return: [bool] success / fail
    def __open_link_in_enrollment_action_menu(self, viable_enrollment_list, link_name):
        label_enrollment_row_name_xpath = ('//table[@id="wp85039573formResultSet"]/tbody//td[6]')
        links_enrollment_action_ids = {'Edit Enrollment': 'amb3',
                                       'Edit Project Entry Workflow': 'amb4'}

        menu_id = 'ActionMenu'
        link_id = links_enrollment_action_ids[link_name]
        
        # assign priority values to make variables less mutable
        # realized it has the same complexity time as the way I matched names
        # I don't know why I made it more complicated for myself lol
        enrollment_ranking_dict = {}
        for i in range(len(viable_enrollment_list)):
            enrollment_ranking_dict[viable_enrollment_list[i]] = i

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.visibility_of_element_located((By.XPATH, label_enrollment_row_name_xpath))
            )
            rows_enrollment_xpath = '//table[@id="wp85039573formResultSet"]/tbody/tr'
            cont = True

            rows_enrollment = self.browser.find_elements(By.XPATH, rows_enrollment_xpath)
            stored_ranking = len(enrollment_ranking_dict)
            for row in rows_enrollment:
                if not cont:
                    break
                # if row is a header (i.e. Active, Exited)
                if row.get_attribute("class") == "gbHead":
                    # prevent from clicking on an expired enrollment
                    label = row.find_element(By.XPATH, './td/a')
                    if label.get_attribute("data-value") == "Exited":
                        cont = False
                        break
                # if row contains enrollment data
                else:
                    label_enrollment_name = row.find_element(By.XPATH, './td[6]').text
                    for enrollment, ranking in enrollment_ranking_dict.items():
                        if enrollment in label_enrollment_name and ranking < stored_ranking:
                            # ranking indicates that we'd like to update newer enrollments over older ones
                            stored_ranking = ranking
                            # get the parent element of where the label is located
                            stored_row = row
                            break
            # For Loop End

            # click the best match
            if stored_ranking < len(enrollment_ranking_dict):
                menu_action = stored_row.find_element(By.CLASS_NAME, 'action-menu')
                self.browser.execute_script("arguments[0].scrollIntoView();", menu_action)
                time.sleep(1)
                menu_action.click()
            else:
                return False
        except Exception as e:
            print("Couldn't open Enrollment Action Menu")
            print(traceback.format_exc())
            return e

        # wait for action menu to appear
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.visibility_of_element_located((By.ID, menu_id))
            )
        except Exception as e:
            print("Couldn't find Action Menu")
            print(traceback.format_exc())
            return e

        # select the desired link option from the action menu
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, link_id))
            )
            link = self.browser.find_element(By.ID, link_id)
            link.click()
        except Exception as e:
            print("Couldn't click link in Action Menu")
            print(traceback.format_exc())
            return e
        return True

    # Cancels the workflow of an enrollment / intake process by clicking cancel and hitting yes on the popup
    # @return: [bool] success / fail 
    def __cancel_intake_workflow(self):
        button_cancel_workflow_xpath = '//div[@class="workflow-controls"]/button[@aria-label="Cancel the workflow"]'
        button_dialog_yes_id = 'YesButton'

        self.__wait_until_page_fully_loaded("Intake")
        self.browser.switch_to.default_content()
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, button_cancel_workflow_xpath))
            )
            button_cancel_workflow = self.browser.find_element(By.XPATH, button_cancel_workflow_xpath)
            button_cancel_workflow.click()

            self.browser.switch_to.default_content()
            # update id for iframe, it increments by one every time its open
            # which like... why ????? who coded this ???
            current_dialog_iframe = self.iframe_dialog_id + str(self.iframe_dialog_counter)
            self.iframe_dialog_counter += 1
            self.__switch_to_iframe(current_dialog_iframe)
            WebDriverWait(self.browser, self.wait_time).until(EC.element_to_be_clickable((By.ID, button_dialog_yes_id)))
            button_dialog_yes = self.browser.find_element(By.ID, button_dialog_yes_id)
            button_dialog_yes.click()
        except Exception as e:
            print("Couldn't cancel the Intake workflow")
            print(traceback.format_exc())
            return False
        return True

    '''
    ------------------------ HELPER ------------------------
    '''

    # Returns a ratio showing how similar two strings are
    # @param: [str] a: string to be compared
    #         [str] b: string to be compared
    # @return: [int] similarity score
    def __similar(self, a, b):
        score = difflib.SequenceMatcher(a=a.lower(), b=b.lower()).ratio()
        return score

    # Waits until a page is fully loaded before continuing
    # @param: [str] page_name: the name of the page to be printed in output to make debug easier
    def __wait_until_page_fully_loaded(self, page_name):
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                lambda browser: browser.execute_script('return document.readyState') == 'complete')
        except Exception as e:
            print("Error loading" + page_name + " page")
            print(traceback.format_exc())
    
    # Similar to the funciton above, best used for waiting for a page with a list of 
    #   results to load i.e. Enrollments, Services by checking for result set element
    def __wait_until_result_set_fully_loaded(self):
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.visibility_of_element_located((By.ID, "RendererResultSet"))
            )
        except Exception as e:
            print("Error loading frame")
            print(traceback.format_exc())

    # Focus on iframe with given ID
    # @param: [str] iframe_id: id of the iframe to be found
    def __switch_to_iframe(self, iframe_id):
        self.browser.switch_to.default_content()
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, iframe_id))
            )
        except Exception as e:
            print("Couldn't focus on iframe")
            print(traceback.format_exc())