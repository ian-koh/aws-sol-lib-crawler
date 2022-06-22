import io
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException 
from selenium import webdriver
from tempfile import mkdtemp
import pandas as pd
import time
import boto3

def lambda_handler(event, context):

    options = webdriver.ChromeOptions()
    options.binary_location = '/opt/chrome/chrome'
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")
    driver = webdriver.Chrome("/opt/chromedriver",
                              options=options)
    driver.get("https://aws.amazon.com/solutions/browse-all/")
    
           
    def check_exists_by_xpath(xpath):
        try:
            driver.find_element_by_xpath(xpath)
        except NoSuchElementException:
            return False
        return True

#On first run, crawl all solutions and save it in a excel sheet

#1. Select checkbox AWS Solutions
    time.sleep(3)
    try:
        element = WebDriverWait(driver,20).until(EC.presence_of_element_located((By.XPATH,"/html/body/div[1]/div/div[1]/div/div/div/div/button[2]")))
        element.click()
    except:
        print("Error")
    element_1 = WebDriverWait(driver,20).until(EC.presence_of_element_located((By.XPATH,"/html/body/div[2]/main/div[4]/div[1]/div[2]/div[2]/div/div[2]/div/div[1]/input")))
    element_1.click()
    #For each technology checkbox, take the title loop through the different cards
    #tech_category_checkboxes_group = driver.find_elements_by_css_selector("input[data-key='tech-category']")
    tech_category_checkboxes_group = driver.find_elements_by_class_name("lb-checkbox")
    list_of_use_cases = []
    counter = 0
    for i in range(3, len(tech_category_checkboxes_group)):
        driver.switch_to.window(driver.window_handles[0])
        tech_category = tech_category_checkboxes_group[i]
        tech_category_checkbox = tech_category.find_element_by_css_selector("input")
        tech_category_label = tech_category.find_element_by_css_selector("label").text
        #check tech_category checkbox
        select= WebDriverWait(tech_category, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input'))).click()

        #tech_category_checkbox.click()
        time.sleep(1)
        #After clicking
        topics_headlines_and_link = driver.find_elements_by_class_name("m-headline")
        topics_descriptions = driver.find_elements_by_class_name("m-desc")
        #Loop through the number of cards in the page
        
        for o in range (len(topics_descriptions)):
            list_of_products=[]
            #click on each card
            
            a_tag_click = driver.find_element_by_xpath("/html/body/div[2]/main/div[4]/div[2]/div/div[2]/div[3]/section/ul/li["+str(o+1)+"]/div[1]/div[2]/div/h2/a").click()
            current_topic = topics_headlines_and_link[o]
            topic_site_url = current_topic.find_element_by_css_selector("h2 a").get_attribute("href")
            topic_title = current_topic.find_element_by_css_selector("h2 a").text
            topic_description = topics_descriptions[o].text
            counter+=1
            driver.switch_to.window(driver.window_handles[counter])

            #Click on Resources & FAQ
            #driver.implicitly_wait(1)
            #If resources and FAQ path exists
            #is_present = driver.find_elements_by_xpath("/html/body/header/div[3]/div/div/div[2]/a[2]")
            time.sleep(1)
            if check_exists_by_xpath("/html/body/header/div[3]/div/div/div[2]/a[2]"):
                driver.find_element_by_xpath("/html/body/header/div[3]/div/div/div[2]/a[2]").click()
                #Click on resources and FAQ button
                time.sleep(1)
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "Related_AWS_products")))
                #Get all the products elements

                products_div = driver.find_element_by_id("Related_AWS_products").find_element_by_xpath('..').find_elements_by_class_name("lb-rtxt")
                for i in range(1,len(products_div)):
                    try:
                        product = products_div[i]
                        WebDriverWait(product, 20).until(EC.presence_of_element_located((By.XPATH, "./p/a")))
                        current_product = product.find_element_by_xpath("./p/a").get_attribute("innerHTML")
                    except:
                        
                        continue
                    list_of_products.append(current_product)
                    print(current_product)
            
            item_list = [tech_category_label, topic_title, topic_site_url, topic_description, list_of_products]
            list_of_use_cases.append(item_list)
            #switch back to main window
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(1)
        #Need to scroll up
        driver.execute_script("window.scrollTo(0, 220)")
        #Unselect current category
        unselect= WebDriverWait(tech_category, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input'))).click()


    df = pd.DataFrame(list_of_use_cases, columns=["Category","Topic","Site URL","Topic Description","List Of Products"])
    writer = pd.ExcelWriter('text.xlsx',engine='xlsxwriter')
    df.to_excel(writer, sheet_name='SolLibUseCase', index=False)
    writer.save()

    with io.BytesIO() as output:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer)
        data = output.getvalue()

    s3 = boto3.resource('s3')
    s3.Bucket('aws-sol-lib-use-case-crawler-12345').put_object(Key='data.xlsx', Body=data)


    #CDK to contain s3 bucket
    #grant s3 permissions to Lambda
    #take in parameters upon cdk dpeloy for s3 bucket name and object name
    #create ECR repository
    #lambda needs to be 15 minute timeout and 1000mb in storage