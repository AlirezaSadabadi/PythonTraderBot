__author__ = "Alireza Sadabadi"
__copyright__ = "Copyright (c) 2025 Alireza Sadabadi. All rights reserved."
__credits__ = ["Alireza Sadabadi"]
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Alireza Sadabadi"
__email__ = "alirezasadabady@gmail.com"
__status__ = "Test"
__doc__ = "you can see the tutorials in https://youtube.com/@alirezasadabadi?si=d8o7LK_Ai1Hf68is"

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import quote
import feedparser

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np

# if this feature is true you need to install playwright
# it installs chromium automatically
# it might need to install chrome for support chromium
# python -m playwright install
analyseContent = False

finbert_model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
labels = ['Positive', 'Negative', 'Neutral']

# finbert_model = AutoModelForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone")
# finbert_tokenizer = AutoTokenizer.from_pretrained("yiyanghkust/finbert-tone")
# labels = ['Neutral','Positive', 'Negative']

def FetchNewsContent(url):
    try:
        
        #with selenium better load the content of the page but it's slow
        # driver = webdriver.Firefox()
        # driver.implicitly_wait(30)
        # delay = 2 #increase delay if the content doesn't get completely
        # pageNumber = 1
        # driver.get(url)
        # for i in range(pageNumber):
        #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        #     time.sleep(delay)
        # html_source = driver.page_source
        # data = html_source.encode('utf-8')
        # driver.quit()

        # playwright completely get the page content in good manner
        # however the library is really heavy to install
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # Launches a headless browser
            page = browser.new_page()
            page.goto(url)
            # Wait for the page to load or use a custom wait condition
            page.wait_for_timeout(2000)  # Wait for 2 seconds
            data = page.content()  # Get the fully loaded HTML
            browser.close()

        bs4soup = BeautifulSoup(data, "html.parser")
        paragraphs = bs4soup.find_all("p")
        content = ' '.join([paragraph.get_text() for paragraph in paragraphs])
        return content.strip()
    except:
        return "Content not accessible"
    

def FetchNews(query, newsCountPerQuery=10):
    global analyseContent
    url = f"https://news.google.com/rss/search?q={quote(query)}"
    rss_feed = feedparser.parse(url)
    newsItems = rss_feed.entries[:newsCountPerQuery]

    news = []
    for item in newsItems:
        title = item.title
        published = item.published
        link = item.link
        if analyseContent == True:
            content = FetchNewsContent(link)
        else:
            content = ''
        
        news.append({
            "title": title,
            "published": published,
            "link": link,
            "content": content
        })

    return news


def SentimentClassifier(text):
    if not text.strip():
        return 0.0, 'Neutral'

    inputs = finbert_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = finbert_model(**inputs)

    logits = outputs.logits
    probabilities = torch.softmax(logits, dim=1).numpy()[0]
    max_index = np.argmax(probabilities)
    sentiment = labels[max_index]

    return sentiment

    #######################################################################################
    # there is a shortage of capital, and we need extra financing ---- negative
    # growth is strong and we have plenty of liquidity ---- positive
    # there are doubts about our finances ---- negative or neutral
    # profits are flat ---- neutral
    ########################################################################################

def SentimentsSummarize(news):

    global analyseContent

    summary = {
        "Positive": 0,
        "Negative": 0,
        "Neutral": 0
    }

    for item in news:
        text = item['title'] + " " + item['content'] if analyseContent else item['title']
        sentiment = SentimentClassifier(text)
        summary[sentiment] += 1

    total = len(news)
    print("\n*** Market Sentiment Summary ***")
    print(f"Total News Analyzed: {total}")
    for sentiment, count in summary.items():
        percent = (count / total) * 100
        print(f"{sentiment}: {count} ({percent:.2f}%)")

def main():
    global analyseContent

    # sentences = ["there is a shortage of capital, and we need extra financing", 
    #          "growth is strong and we have plenty of liquidity", 
    #          "there are doubts about our finances", 
    #          "profits are flat"]
    
    # for id, sent in enumerate(sentences):
    #     sentiment = SentimentClassifier(sent)



    queries = [
        "gold market",
        "gold price",
        "gold trading",
        "gold futures",
        "gold bullion",
        "gold demand",
        "gold supply",
        "gold spot price",
        "gold ETF",
        "gold investment"
    ]
 
    newsCountPerQuery = 3
    allNews = []

    for query in queries:
        print(f"Fetching news for '{query}' ....\n")
        news = FetchNews(query, newsCountPerQuery)
        allNews.extend(news)

    for newsId, news in enumerate(allNews, 1):
        print(f"News {newsId}: {news['title']}")
        print(f"Published: {news['published']}")
        print(f"Link: {news['link']}")

        text = news['title'] + " " + news['content'] if analyseContent else news['title'] 
        sentiment = SentimentClassifier(text)
        print(f"Sentiment: {sentiment}\n")

    SentimentsSummarize(allNews)

if __name__ == "__main__":
    main()