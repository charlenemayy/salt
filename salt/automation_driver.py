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
    wait_time = 10

    def __init__(self):
        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)
        self.browser = Chrome(options=chrome_options)

    # Setup
    def open_clienttrack(self):
        self.browser.get('https://clienttrack.eccovia.com/login/HSNCFL')

    # Login to Client Track
    def login_clienttrack(self, username, password):
        field_username = self.browser.find_element(By.ID, "UserName")
        field_password = self.browser.find_element(By.ID, "Password")

        field_username.send_keys(username)
        field_password.send_keys(password)
        field_password.send_keys(Keys.RETURN)
    
    # Navigate to 'Client Dashboard' page
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
            print(e)
            return False

        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, button_nav_dashboard_page_id))
            )
            button_dashboard = self.browser.find_element(By.ID, button_nav_dashboard_page_id)
            button_dashboard.click()
        except Exception as e:
            print("Couldn't navigate to 'Dashboard' page")
            print(e)
            return False

    # Navigate to 'Find Client' page
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
            print(e)
            return False
        return True

    # Search for a Client by their ID number and checks that the name is a relative match once found
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
            print(e)
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
            print("Current Client: " + first_name, last_name)
            print("Loaded Client: " + dashboard_first_name, dashboard_last_name)
            print("Similarity Score: ", max(final_score_one, final_score_two))
            return False
        except Exception as e:
            print("Couldn't find correct Client Name")
            print(e)
            return False

    # Search for client by their birthday and selects their name from a list
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
            print(e)
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
                        print()
            # For Loop End

            if result_max_score > 0:
                stored_result.click()
                return True

            print("Couldn't find client name among results")
            return False
        except Exception as e:
            print("Error finding list of results")
            print(e)
            return False
    
    # Navigates to the list of services page for the client, assumes the browser is at the Client Dashboard
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
            print(e)
            return False
        return True
    
    # Navigates to the edit enrollment page for client, assumes the browser is at the Client Dashboard
    def navigate_to_edit_enrollment(self, viable_enrollment_list):
        self.__wait_until_page_fully_loaded("Client Dashboard")
        self.__switch_to_iframe(self.iframe_id)

        return self.__open_link_in_enrollment_action_menu(viable_enrollment_list, "Edit Enrollment")


    # Find a favorable enrollment on the client dashboard and open its corresponding action menu
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

    # Updates the date of engagement field in the "Edit Enrollment" page to be the date of service 
    def update_date_of_engagement(self, viable_enrollment_list, service_date):
        table_row_family_members_xpath = '//table[@id="RendererSF1ResultSet"]//tbody/tr'
        field_date_of_engagement_xpath = '//table[@id="RendererSF1ResultSet"]/tbody/tr/td/span/input'
        button_save_id = "Renderer_SAVE"

        self.__switch_to_iframe(self.iframe_id)
        self.__wait_until_page_fully_loaded('Edit Enrollment')

        if isinstance(self.navigate_to_edit_enrollment, Exception):
            return False

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

    # Enter all the services associated with current client, service_date must be numeric values only
    def enter_client_services(self, viable_enrollment_list, service_date, services_dict):
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
                                  'Food' : '359'}
        
        field_units_id = "1000007095_Renderer"
        field_date_id = "1000007086_Renderer"
        button_save_id = "Renderer_SAVE"

        # for now only street outreach can update date of engagement
        DoE_enrollment_list = [x for x in viable_enrollment_list if 'Street' in x]

        # update date of engagement and enroll client if not already enrolled
        # if fails, do nothing; automation will enroll them anyway when entering services
        # and thus keep the date of engagement updated
        if not self.update_date_of_engagement(DoE_enrollment_list, service_date):
            print("Couldn't update date of engagement, will enroll client")
        self.__wait_until_page_fully_loaded('Enrollment')
        self.__wait_until_result_set_fully_loaded()

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
                print(e)
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
                    print("Client is not enrolled -- Enrolling client")
                    self.navigate_to_client_dashboard()
                    if not self.enroll_client(service_date):
                        return False

                    print("Successfully enrolled client -- Entering services")
                    return self.enter_client_services(viable_enrollment_list, service_date, services_dict)
            except Exception as e:
                print("Error finding enrollment")
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
                print(e)
                return False
        # For Loop End - Success!
        return True
    
    def enroll_client(self, service_date):
        button_new_enrollment_id = "Renderer_1000000248"
        dropdown_veteran_status_id = "1000006680_Renderer"
        option_data_not_collected_value = "99"
        button_finish_id = "Renderer_SAVE"
        button_save_and_close_id = "Renderer_SAVEFINISH"
        dropdown_project_id = "1000004260_Renderer"
        option_salt_orl_enrollment_value = "1217"
        dropdown_rel_to_head_of_household_xpath = '//table[@id="RendererSF1ResultSet"]//tr/td/select'
        field_project_date_xpath = '//table[@id="RendererSF1ResultSet"]//tr/td/span[@class="DateField input-group"]/input'
        field_date_of_engagement_xpath = '//table[@id="RendererSF1ResultSet"]//tr/td/span[@class="DateField input-group"]/input'
        button_save_id = "Renderer_SAVE"
        table_row_family_members_xpath = '//table[@id="RendererSF1ResultSet"]//tbody/tr'

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
            print(e)
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
            print("Couldn't update Veteran Status")
            print(e)
            return False

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
            print(e)
            return False

        # wait until 'Program Enrollment' section loads
        self.__switch_to_iframe(self.iframe_id)
        self.__wait_until_page_fully_loaded('Intake - Program Enrollment')
        
        # select 1217 - SALT Outreach - ORL ESG Street Outreach:SO
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.ID, dropdown_project_id))
            )
            dropdown_option_xpath = '//select[@id="%s"]//option[@value="%s"]' %(dropdown_project_id, option_salt_orl_enrollment_value)
            option_salt_orl = self.browser.find_element(By.XPATH, dropdown_option_xpath)
            option_salt_orl.click()
            time.sleep(1)
        except Exception as e:
            print("Couldn't find SALT ORL Enrollment in options")
            print(e)
            return False

        # update household data for program enrollment and only enroll current client (not family members)
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, dropdown_rel_to_head_of_household_xpath))
            )
            # TODO: fix code for when household has multiple members -- rare case
            # find correct household member (check by name?)
            # click 'SELF' option
            rows_family_members = self.browser.find_elements(By.XPATH, table_row_family_members_xpath)
            if len(rows_family_members) > 1:
                print("More than one family member to enroll, please enroll manually")
                self.cancel_intake_workflow()
                return False

            time.sleep(1)
            field_project_date = self.browser.find_elements(By.XPATH, field_project_date_xpath)[2]
            self.browser.execute_script("arguments[0].scrollIntoView();", field_project_date)
            time.sleep(1)
            WebDriverWait(self.browser, self.wait_time).until(EC.element_to_be_clickable(field_project_date))
            field_project_date.click()
            time.sleep(1)
            field_project_date.clear()
            time.sleep(1)
            field_project_date.send_keys(service_date)
            time.sleep(1)

            field_date_of_engagement = self.browser.find_elements(By.XPATH, field_date_of_engagement_xpath)[3]
            self.browser.execute_script("arguments[0].scrollIntoView();", field_date_of_engagement)
            time.sleep(1)
            WebDriverWait(self.browser, self.wait_time).until(EC.element_to_be_clickable(field_date_of_engagement))
            field_date_of_engagement.click()
            time.sleep(1)
            field_date_of_engagement.clear()
            time.sleep(1)
            field_date_of_engagement.send_keys(service_date)
            time.sleep(1)
            button_save = self.browser.find_element(By.ID, button_save_id)
            button_save.click()
            time.sleep(2)
        except Exception as e:
            print("Couldn't update household")
            print(e)
            self.cancel_intake_workflow()
            time.sleep(2)
            return False
        
        # cancel the workflow assessment -- not enough information has been provided for us to do an assessment
        return self.cancel_intake_workflow()

    def cancel_intake_workflow(self):
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
            print(e)
            return False
        return True
    
    # Navigates to a list of the Client's enrollments, assumes already on Client Dashboard page
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
            print(e)
            return False
        return True
    
    # Returns a ratio showing how similar two strings are
    def __similar(self, a, b):
        score = difflib.SequenceMatcher(a=a.lower(), b=b.lower()).ratio()
        return score

    # Waits until a page is fully loaded before continuing
    def __wait_until_page_fully_loaded(self, page_name):
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                lambda browser: browser.execute_script('return document.readyState') == 'complete')
        except Exception as e:
            print("Error loading" + page_name + " page")
            print(e)
    
    # Best used for waiting for a page with a list of results to load i.e. Enrollments, Services
    def __wait_until_result_set_fully_loaded(self):
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.visibility_of_element_located((By.ID, "RendererResultSet"))
            )
        except Exception as e:
            print("Error loading frame")
            print(traceback.format_exc())

    # Focus on iframe with given ID
    def __switch_to_iframe(self, iframe_id):
        self.browser.switch_to.default_content()
        try:
            WebDriverWait(self.browser, self.wait_time).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, iframe_id))
            )
        except Exception as e:
            print("Couldn't focus on iframe")
            print(e)
    