from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Firefox
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import sys
import json
from win32process import CREATE_NO_WINDOW
import time
from selenium.common import exceptions
import json
from selenium.webdriver.common.keys import Keys
from fake_useragent import UserAgent


# returns a chrome webdriver with added options
# careful: dnb.com does not build webelements in headless mode
def getChromeDriver():
    chrome_options = Options()
    ua = UserAgent()
    userAgent = ua.chrome
    chrome_options.add_argument("no-sandbox");
    chrome_options.add_argument('user-agent=' + userAgent)
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--window-size=1920,1080")
    # chrome_options.add_argument("--incognito")
    # chrome_options.headless = True
    chrome_options.add_argument("--headless")

    # chrome_options.add_argument("--hidecommandpromptwindow")
    chrome_driver = os.getcwd() + "\\chromedriver.exe"
    args = ["hide_console", ]

    return webdriver.Chrome(options=chrome_options, executable_path=chrome_driver, service_args=args)


# this method builds the search query url for a specific company on dnb.com, avoiding the manual search for the company.
# Again, clicking on the company in the search result denies access to the server. 
def scrape2(company):
    driver = getChromeDriver()
    driver.get("https://www.dnb.com/business-directory/company-search.html?term=" + company + "&page=1")

    timeout = 10

    try:
        element_present = EC.presence_of_element_located((By.ID, 'company_results'))
        WebDriverWait(driver, timeout).until(element_present)
        time.sleep(1)
    except TimeoutException as e:
        driver.quit()
        return ("failed")

    try:
        no_result = driver.find_element_by_id("no_results_message")
        driver.quit()
        return ("no results")

    except exceptions.NoSuchElementException as e:
        try:
            minimal_name = "This is an extra long string so that the first time len() < actually hopefully successfully works!"
            minimal_names_link = ""
            results = driver.find_elements_by_class_name('row.search_result')
            print(len(results))
            for result in results:
                country = result.find_element_by_class_name('country')
                # print("The country: " + country.text)
                primary_name = result.find_element_by_class_name('primary_name')
                if country.text == "Germany" and company.lower() in primary_name.text.lower() and len(
                        primary_name.text.lower()) < len(minimal_name):
                    minimal_name = primary_name.text.lower()
                    a = primary_name.find_elements_by_tag_name("a")[0]
                    minimal_names_link = a.get_attribute("href")
            if minimal_names_link != "":
                driver.quit()
                return minimal_names_link
            else:
                driver.quit()
                return ("not in db")

        except exceptions.NoSuchElementException as e:
            driver.quit()
            return "failed"


def scrape3(company_link):
    driver = getChromeDriver()
    driver.get(company_link)
    try:
        body = driver.find_element_by_class_name("company_info_body.module_body")
    except exceptions.NoSuchElementException as e:
        print(e)

    try:
        field_employees = body.find_element_by_class_name("empCon")
        n_employees = field_employees.find_element_by_class_name("value").text
    except exceptions.NoSuchElementException as e:
        try:
            field_employees = body.find_element_by_class_name("emp")
            n_employees = field_employees.find_element_by_class_name("value").text
        except exceptions.NoSuchElementException as e:
            n_employees = "missing"

    try:
        field_sales = body.find_element_by_class_name("sales")
        n_sales = field_sales.find_element_by_class_name("value").text
    except exceptions.NoSuchElementException as e:
        n_sales = "missing"

    try:
        location = driver.find_element_by_class_name("company_postal").text
    except exceptions.NoSuchElementException as e:
        location = "missing"

    driver.quit()
    return n_employees, n_sales, location


# initialize counters
prob_SME = 0
big = 0
micro = 0

# initialize time for ETA prediction (only works when scraping from index 0)
start = time.time()

# load last saved index, if it exists
try:
    with open('current_index.json', 'r') as file:
        save_list = json.load(file)
        index = save_list[0]
        const_index = index
        prob_SME = save_list[1]
        big = save_list[2]
        micro = save_list[3]
except:
    index = 0
    const_index = index
    prob_SME = 0
    big = 0
    micro = 0
# get company name list
with open('company_names.json', 'r') as file1:
    name_list = json.load(file1)

# get last saved output to continue with, if not existing, create new list
try:
    with open('output/company_attributes.json', 'r') as file2:
        companies = json.load(file2)
except:
    companies = []

# loop through company name list
while index < len(name_list):

    name = name_list[index]
    print(str(index) + "/" + str(len(name_list)))
    print(name)
    company_link = scrape2(name)
    print(company_link)

    # retry scrape if dnb didn't return any results, sometimes searching in dnb doesn't work
    while company_link == "failed":
        company_link = scrape2(name)
    if company_link == "no results":
        company_link = scrape2(name)
    if company_link == "no results":
        company_link = scrape2(name)
    if company_link == "not in db" or company_link == "no results":
        index +=1
        continue
    # Print company_link again just to see, whether 'no results' has changed into an actual link (happened already)
    print(company_link)

    # get all necessary information from company link website and return results as array, since location field might
    # have more than 2 parameters
    n_employees, n_sales, location = scrape3(company_link)
    words = location.split(",")
    try:
        plz = words[0]
        city = words[1]
    except:
        plz = "missing"
        city = "missing"

    # Check in which range the company is: SME (10 - 249 and 0,7 - 39,9), Micro or Big
    # In prob_SME are all companies which have only given one criteria or at least one criteria is within the SME range
    print("Mitarbeiter: " + str(n_employees.replace(",", "")))
    print("Umsatz: " + str(n_sales))
    print("Ort:" + plz + " " + city)
    if (n_employees != "missing" and int(n_employees.replace(",", "")) < 10) and (
            n_sales != "missing" and float(n_sales.replace(",", "")) < 0.7):
        micro += 1
    elif (n_employees != "missing" and int(n_employees.replace(",", "")) >= 250) and (
            n_sales != "missing" and float(n_sales.replace(",", "")) >= 40):
        big += 1
    else:
        prob_SME += 1
        # add company attributes to list
        companies.append([name, n_employees, n_sales, plz, city])

    # increase index counter
    index += 1

    # create save state every 10 iterations
    if index % 10 == 0:
        # calculate and print ETA time
        current = time.time()
        sys.stdout.write('\r' + 'ETA:' + str(
            int(((current - start) / index * (len(name_list) - const_index) / 60) - (
                        current - start) / 60)) + ' Minuten' + '\n')
        sys.stdout.flush()

        # save current index
        with open('current_index.json', 'w') as f:
            save_list = [index, prob_SME, big, micro]
            json.dump(save_list, f)

        # save current company list
        with open('output/company_attributes.json', 'w') as f1:
            json.dump(list(companies), f1)

        print("Nach " + str(index - 1) + " Unternehmen haben " + str(
            prob_SME) + " wahrscheinlich die richtige Größe oder nur eine Angabe. " + str(
            micro) + " sind eigentlich zu klein. " + str(big) + " sind zu groß.")

print("Wahrscheinlich richtige Größe oder nur eine Angabe: " + str(prob_SME) + ", eigentlich zu klein: " + str(
    micro) + ", eigentlich zu groß: " + str(big))

#final save when scraping is done
with open('output/company_attributes.json', 'w') as f1:
    json.dump(list(companies), f1)