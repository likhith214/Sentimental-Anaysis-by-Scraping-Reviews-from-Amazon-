import streamlit as st
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
from transformers import pipeline
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# Custom headers for requests
custom_headers = {
    "Accept-language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "User-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
}

# Function to get BeautifulSoup object
# def get_soup(url):
#     response = requests.get(url, headers=custom_headers)
#     if response.status_code != 200:
#         print("Error in getting webpage")
#         exit(-1)
#     soup = BeautifulSoup(response.text, "lxml")
#     return soup

# Function to get reviews
def get_reviews(soup):
    review_elements = soup.select("div.review")
    scraped_reviews = []
    for review in review_elements:
        r_author_element = review.select_one("span.a-profile-name")
        r_author = r_author_element.text if r_author_element else None
        r_rating_element = review.select_one("i.review-rating")
        r_rating = r_rating_element.text.replace("out of 5 stars", "") if r_rating_element else None
        r_title_element = review.select_one("a.review-title")
        r_title_span_element = r_title_element.select_one("span:not([class])") if r_title_element else None
        r_title = r_title_span_element.text if r_title_span_element else None
        r_content_element = review.select_one("span.review-text")
        r_content = r_content_element.text if r_content_element else None
        r_date_element = review.select_one("span.review-date")
        r_date = r_date_element.text if r_date_element else None
        r_verified_element = review.select_one("span.a-size-mini")
        r_verified = r_verified_element.text if r_verified_element else None
        r_image_element = review.select_one("img.review-image-tile")
        r_image = r_image_element.attrs["src"] if r_image_element else None
        r = {
            "author": r_author,
            "rating": r_rating,
            "title": r_title,
            "content": r_content,
            "date": r_date,
            "verified": r_verified,
            "image_url": r_image
        }
        scraped_reviews.append(r)
    return scraped_reviews

# Function to click "See more reviews" button using Selenium
def click_see_more_reviews(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode (without UI)
    service = Service('chromedriver-win64\chromedriver.exe')  # Replace 'path_to_chromedriver' with the path to your chromedriver executable
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)
    # Add a delay to allow page to load
    time.sleep(3)
    try:
        # Locate the "See more reviews" button and click it
        see_more_button = driver.find_element(By.CSS_SELECTOR, "a[data-hook='see-all-reviews-link-foot']")
        see_more_button.click()
        # Add a delay to allow the reviews to load
        time.sleep(3)
        # Get the current page source after clicking "See more reviews"
        updated_page_source = driver.page_source
        return driver, updated_page_source
    except Exception as e:
        print(e)
    finally:
        # driver.quit()
        pass

# Function to click "Next page" link using Selenium
def click_next_page(driver):
    try:
        next_page_link = driver.find_element(By.CSS_SELECTOR, "li.a-last > a")
        next_page_url = next_page_link.get_attribute("href")
        driver.get(next_page_url)
        # Add a delay to allow the next page to load
        time.sleep(3)
        return True
    except:
        return False

# Main function to scrape reviews and perform sentiment analysis
def main():
    st.title("Amazon Product Review Sentiment Analysis")
    url = st.text_input("Enter the Amazon product URL")

    if url:
        with st.spinner("Scraping reviews..."):
            driver, updated_page_source = click_see_more_reviews(url)
            soup = BeautifulSoup(updated_page_source, "lxml")
            data = get_reviews(soup)

            try:
                has_next_page = True
                while has_next_page:
                    has_next_page = click_next_page(driver)
                    updated_page_source = driver.page_source
                    soup = BeautifulSoup(updated_page_source, "lxml")
                    data += get_reviews(soup)
            finally:
                driver.quit()

        df = pd.DataFrame(data=data)
        st.write("## Scraped Reviews", df)

        # Sentiment Analysis using BERT
        sentiment_pipeline = pipeline("sentiment-analysis")

        def get_bert_sentiment(review):
            result = sentiment_pipeline(review[:512])  # BERT has a max token limit
            return result[0]['label'], result[0]['score']

        df[['sentiment_label', 'sentiment_score']] = df['content'].apply(lambda x: pd.Series(get_bert_sentiment(x)))
        st.write("## Sentiment Analysis Results", df[['author', 'rating', 'title', 'content', 'sentiment_label', 'sentiment_score']])

        # Sentiment Distribution
        st.write("## Sentiment Distribution")
        st.bar_chart(df['sentiment_label'].value_counts())
        
        
        
        # Sentiment Distribution
        st.write("## Sentiment Distribution")
        sentiment_counts = df['sentiment_label'].value_counts()
        fig, ax = plt.subplots()
        ax.pie(sentiment_counts, labels=sentiment_counts.index, autopct='%1.1f%%', startangle=90,shadow=True)
        ax.axis('equal')  # Equal aspect ratio ensures the pie chart is circular.
        st.pyplot(fig)


        # Word Cloud for Positive Reviews
        positive_reviews = ' '.join(df[df['sentiment_label'] == 'POSITIVE']['content'])
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(positive_reviews)


        st.write("## Word Cloud for Positive Reviews")
        fig, ax = plt.subplots()
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)

if __name__ == '__main__':
    main()



