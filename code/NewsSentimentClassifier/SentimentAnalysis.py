from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import quote
import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# if this feature is true you need to install playwright
# it installs chromium automatically
# it might need to install chrome for support chromium
# python -m playwright install
analyseContent = False

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
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(text)
    polarity = scores['compound']
    if polarity < -0.05:
        sentiment = 'Negative'
    elif polarity > 0.05:
        sentiment = 'Positive'
    else:
        sentiment = 'Neutral'

    return polarity, sentiment


def SentimentsSummarize(news):

    global analyseContent

    summary = {
        "Positive": 0,
        "Negative": 0,
        "Neutral": 0
    }

    for item in news:
        text = item['title'] + " " + item['content'] if analyseContent else item['title']
        _, sentiment = SentimentClassifier(text)
        summary[sentiment] += 1

    total = len(news)
    print("\n*** Market Sentiment Summary ***")
    print(f"Total News Analyzed: {total}")
    for sentiment, count in summary.items():
        percent = (count / total) * 100
        print(f"{sentiment}: {count} ({percent:.2f}%)")

def main():
    global analyseContent
    
    queries = [
        "gold price",
        "gold market",
        "gold trading",
        "gold demand",
        "gold supply"
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
        polarity, sentiment = SentimentClassifier(text)
        print(f"Sentiment: {sentiment} (Polarity: {polarity:.2f})\n")

    SentimentsSummarize(allNews)

if __name__ == "__main__":
    main()