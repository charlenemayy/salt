from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import difflib

'''
Responsible for all automation, all the data should be processed and cleaned before
being sent to this class, i.e. by daily_data.py. All pandas and dataframe 
logic/manipulation should be done outside of this automation class.

I added the selectors to the top of each function in case they are subject to change
on HMIS' website. 
'''
class Driver:
    # Global selectors
    iframe_id = "TabFrame_2"

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
    
    # Focus on iframe with given ID
    def __switch_to_iframe(self, iframe_id):
        try:
            WebDriverWait(self.browser, 30).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, iframe_id))
            )
        except Exception as e:
            print("Couldn't focus on iframe")
    
    # Navigate to 'Find Client' page
    def navigate_to_find_client(self):
        button_nav_clients_page_id = "ws_2_tab"
        button_nav_find_clients_page_id = "o1000000037"

        # find 'Clients' button on left sidebar
        try:
            WebDriverWait(self.browser, 30).until(
                EC.element_to_be_clickable((By.ID, button_nav_clients_page_id))
            )
            button_clients = self.browser.find_element(By.ID, button_nav_clients_page_id)
            button_clients.click()
        except Exception as e:
            print("Couldn't navigate to 'Clients' page")
            return False
        
        # find 'Find Client' button on left sidebar after waiting for client dashboard to fully load
        try:
            WebDriverWait(self.browser, 30).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, self.iframe_id))
            ) 
            self.browser.switch_to.default_content()
            WebDriverWait(self.browser, 30).until(
                EC.element_to_be_clickable((By.ID, button_nav_find_clients_page_id))
            )
            button_find_client = self.browser.find_element(By.ID, button_nav_find_clients_page_id)
            button_find_client.click()
        except Exception as e:
            print("Couldn't open 'Find Client' page")
            return False

    # Search for a Client by their ID number and checks that the name is a relative match once found
    def search_client_by_ID(self, id, first_name, last_name):
        self.navigate_to_find_client()

        field_client_id_id = "1000005942_Renderer"
        button_search_id = "Renderer_SEARCH"
        label_client_name_xpath = "//span[@class = 'entity-info-value'][@aria-label = 'Name']"

        # enter id into client id field
        self.__switch_to_iframe(self.iframe_id)
        try:
            WebDriverWait(self.browser, 30).until(
                EC.element_to_be_clickable((By.ID, field_client_id_id))
            )
            field_client_id = self.browser.find_element(By.ID, field_client_id_id)        
            field_client_id.click()
            field_client_id.send_keys(id)

            button_search_id = self.browser.find_element(By.ID, button_search_id)
            button_search_id.click()
        except Exception as e:
            print("Couldn't find 'Client ID' field")
            return False

        # check that name matches client data and id
        # should load directly to client dashboard
        self.browser.switch_to.default_content()
        try:
            WebDriverWait(self.browser, 30).until(
                EC.presence_of_element_located((By.XPATH, label_client_name_xpath))
            )
            dashboard_name = self.browser.find_element(By.XPATH, label_client_name_xpath).text
            dashboard_first_name = dashboard_name.split(" ", 1)[0]
            dashboard_last_name = dashboard_name.split(" ", 1)[1]

            # sometimes first and last names are swapped, check both scenarios
            if self.__similar(dashboard_first_name, first_name, 0.9) and self.__similar(dashboard_last_name, last_name, 0.9):
                return True
            # sometimes the first and last names are flipped
            elif self.__similar(dashboard_first_name, last_name, 0.9) and self.__similar(dashboard_last_name, first_name, 0.9):
                return True
        except Exception as e:
            print("Couldn't find correct Client Name")
            return False

    # Search for client by their birthday and selects their name from a list
    def search_client_by_birthdate(self, birthdate, first_name, last_name):
        self.navigate_to_find_client()

        field_birthdate_id = "1000005939_Renderer"
        button_search_id = "Renderer_SEARCH"
        table_search_results_rows_xpath = "//table[@id='RendererResultSet']//tbody/tr"

        self.__switch_to_iframe(self.iframe_id)
        try:
            WebDriverWait(self.browser, 30).until(
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
            return False

        try:
            WebDriverWait(self.browser, 30).until(
                EC.visibility_of_all_elements_located((By.XPATH, table_search_results_rows_xpath))
            )
            # search through rows in tables
            table_search_results = self.browser.find_elements(By.XPATH, table_search_results_rows_xpath)
            for result in table_search_results:
                result_first_name = result.find_element(By.XPATH, "td[2]").text
                result_last_name = result.find_element(By.XPATH, "td[3]").text
                if self.__similar(result_first_name, first_name, 0.9) and self.__similar(result_last_name, last_name, 0.9):
                    result.click()
                    break
                # sometimes the first and last names are flipped
                elif self.__similar(result_first_name, last_name, 0.9) and self.__similar(result_last_name, first_name, 0.9):
                    result.click()
                    break
        except Exception as e:
            print("Couldn't find client name among results")
            return False
    
    # Navigates to the list of services page for the client, assumes the browser is at the Client Dashboard
    def navigate_to_service_list(self):
        text_name_xpath = "//span[@id='1000003947_wp220601446form_Display']"
        link_services_xpath = ""

        self.__switch_to_iframe(self.iframe_id)

        # service link xpath requires client's first name (for whatever reason)
        try:
            WebDriverWait(self.browser, 30).until(
                EC.visibility_of_element_located((By.XPATH, text_name_xpath))
            )
            name = self.browser.find_element(By.XPATH, text_name_xpath).text
            first_name = name.split(", ", 1)[1]
            link_services_xpath = '//a[@title="' + first_name + '\'s Services"]'
        except Exception as e:
            print("Couldn't find client first name for Services link")
            print(e)
        try:
            WebDriverWait(self.browser, 30).until(
                EC.element_to_be_clickable((By.XPATH, link_services_xpath))
            )
            link_services = self.browser.find_element(By.XPATH, link_services_xpath)
            link_services.click()
        except Exception as e:
            print("Couldn't click 'Services' link")
            print(e)

    # Enter all the services associated with current client
    def enter_client_services(self, viable_enrollment_list, service_date, services_dict):
        button_add_new_service_id = "Renderer_1000000216"
        dropdown_enrollment_id = "1000007089_Renderer"
        dropdown_service_id = "1000007094_Renderer"

        # the corresponding values that serve as different service codes
        # these keys should line up with the ones in service_dict
        options_service_values = {'Bible Study' : '690',
                                  'Bedding' : '538',
                                  'Clothing' : '526',
                                  'Grooming' : '530',
                                  'Food' : '359'}

        self.navigate_to_service_list()

        # start entering services
        for service, service_count in services_dict.items():
            # wait until 'Services' page is fully loaded and 'Add Service Button' is clickable
            self.browser.switch_to.default_content()
            self.__switch_to_iframe(self.iframe_id)
            self.__wait_until_page_fully_loaded('Service')
            try:
                WebDriverWait(self.browser, 30).until(
                    EC.element_to_be_clickable((By.ID, button_add_new_service_id))
                )
                button_add_new_service = self.browser.find_element(By.ID, button_add_new_service_id)
                button_add_new_service.click()
            except Exception as e:
                print("Couldn't click 'Add New Service' button")
                print(e)
            
            # wait for 'Add Service' page to be fully loaded
            self.__wait_until_page_fully_loaded('Add Service')

            # find viable 'enrollment' option in the drop down list
            try:
                WebDriverWait(self.browser, 30).until(
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
                if not enrollment_found:
                    raise
                    # TODO: develop enroll client automation
                    # enroll the client and try again, enrollment should 
                    # be found in recursive call
                    '''
                    self.enroll_client()
                    self.navigate_to_client_dashboard()
                    self.enter_client_services()
                    return
                    '''
            except Exception as e:
                print("Error finding enrollment")
                print(e)

            # enter corresponding service
            service_code = options_service_values[service]
            dropdown_option_xpath = '//select[@id="%s"]//option[@value="%s"]' %(dropdown_service_id, service_code)
            option_service = self.browser.find_element(By.XPATH, dropdown_option_xpath)
            option_service.click()


        # End of For Loop
            # enter unit value
            # enter date of service
            # click save button
    
    # Returns a ratio showing how similar two strings are
    def __similar(self, a, b, min_score):
        return difflib.SequenceMatcher(a=a.lower(), b=b.lower()).ratio() > min_score

    def __wait_until_page_fully_loaded(self, page_name):
        try:
            WebDriverWait(self.browser, 30).until(
                lambda browser: browser.execute_script('return document.readyState') == 'complete')
        except Exception as e:
            print("Error loading" + page_name + " page")
            print(e)