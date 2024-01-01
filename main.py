from fastapi import FastAPI
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
import re
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import os
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can specify specific origins instead of "*"
    allow_methods=["*"],  # You can restrict HTTP methods (e.g., ["GET", "POST"])
    allow_headers=["*"],  # You can specify specific headers if needed
    allow_credentials=True,  # Set this to True if your frontend sends credentials (cookies, HTTP Basic Auth, etc.)
)
# classifier = pipeline('sentiment-analysis', model='nlptown/bert-base-multilingual-uncased-sentiment')
# stars_list=[]

class SearchRequest(BaseModel):
    url: str

class ReviewResponse(BaseModel):
    reviews: list
class ScrapingRequest(BaseModel):
    url: str

class ScrapingResponse(BaseModel):
    details: list
    reviews: list

class InputURL(BaseModel):
    url: str


chrome_options = webdriver.ChromeOptions()
chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")

def scraping_reviews(url):
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)
    
    
    all_reviews = []
    all_details = []
    

    try:
        driver.get(url)

        last_review_text = ""

        while True:
            reviews = driver.find_elements(By.CSS_SELECTOR, ".c-review-block__title.c-review__title--ltr")
            detail = driver.find_elements(By.CSS_SELECTOR, ".c-review__body")

            if reviews and reviews[-1].text == last_review_text:
                break

            for review in reviews:
                all_reviews.append(review.text)
            for d in detail:
                all_details.append(d.text)
            last_review_text = reviews[-1].text if reviews else ""

            next_buttons = driver.find_elements(By.CSS_SELECTOR, ".bk-icon.-iconset-navarrow_right.bui-pagination__icon")
            if not next_buttons:
                break

            try:
                next_buttons[0].click()
                time.sleep(5)
            except Exception as e:
                print("Error clicking next button:", e)
                break

        return all_reviews, all_details
    finally:
        driver.quit()
@app.post("/scrape_google/", response_model=ReviewResponse)
async def scrape_reviewsss(request: SearchRequest):
    name = request.url
    urls = f"https://www.google.com/maps/search/{name}"
    reviews_dict = []
 
    
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)

    driver.get(urls)
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "html.parser")
    links = soup.find_all("a", href=True)
    extracted_links = [link['href'] for link in links]

    branch_pattern = re.compile(r'^https://www.google.com/maps/place/.*')
    filtered_links = [link for link in extracted_links if branch_pattern.match(link)]

    
    for index, url in enumerate(filtered_links):
        driver.get(url)
        wait = WebDriverWait(driver, 6)
        try:
            time.sleep(5)
            review_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.wiI7pd')))
            for r in review_elements:
                reviews_dict.append(r.text)
        except Exception as e:
            print(f"Error: {e} while scraping {url}")

    driver.quit()
    
    

    return {
    "reviews": reviews_dict,
}
   
@app.post("/scrape_trustpilot/")
async def scrape_reviewss(request: ScrapingRequest):
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)
    
    all_reviews = []
    all_headings = []
    url = request.url

    try:
        driver.get(url)

        while True:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".typography_body-l__KUYFJ.typography_appearance-default__AAY17.typography_color-black__5LYEn"))
                )
                reviews = driver.find_elements(By.CSS_SELECTOR, ".typography_body-l__KUYFJ.typography_appearance-default__AAY17.typography_color-black__5LYEn")
                heading = driver.find_elements(By.CSS_SELECTOR, ".typography_heading-s__f7029.typography_appearance-default__AAY17")
                for review in reviews:
                    all_reviews.append(review.text)
                for head in heading:
                    all_headings.append(head.text)
                current_url = driver.current_url
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                try:
                    next_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".link_internal__7XN06.button_button__T34Lr.button_m__lq0nA.button_appearance-outline__vYcdF.button_squared__21GoE.link_button___108l.pagination-link_next__SDNU4.pagination-link_rel__VElFy"))
                    )

                    # Scroll to and click the 'Next' button
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(2)

                    # Check if the URL has changed
                    WebDriverWait(driver, 10).until(EC.url_changes(current_url))
                except TimeoutException:
                    # URL did not change after waiting, likely reached the last page
                    print("Last page reached or 'Next' button not clickable.")
                    break

            except NoSuchElementException as e:
                print("Reached the end or encountered an error:", e)
                break

    finally:
        driver.quit()
   
    return ScrapingResponse(details=all_reviews, reviews=all_headings)
@app.post("/scrape_booking/")
async def scrape_data(input_url: InputURL):
    score=[]
    url = input_url.url
    reviews, details = scraping_reviews(url)


    result = {
        "reviews": reviews,
        "details": details}



    return result
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
