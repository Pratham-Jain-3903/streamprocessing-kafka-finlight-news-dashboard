import requests 
import pandas as pd
import os


#-----------------------------#
# NewsFetcher Class fetches news articles from the NewsAPI every few minutes or hours
#-----------------------------#

class NewsFetcher:

    def __init__(self):
        self.api_key = os.getenv("FINLIGHT_API_KEY", "sk_621d88dfcc31a1d3efa89a2873d394563f53bfd6fe1c7aec2ffd22e45d7b1d44")
        self.fetch_news_post_url = "https://api.finlight.me/v2/articles"
        self.fetch_news_sources_get_url = "https://api.finlight.me/v2/sources"

    def fetch_news_post(self, query,sources=[None],exclude_sources=None,countries=None,language="en",from_date=None,to_date=None, order_by="publishDate",order="DESC",page_size=20, page_count=1):
        """
        Fetch news articles based on a query using POST request.
        demo curl : "curl -X 'POST' 'https://api.finlight.me/v2/articles' \
                        -H 'accept: application/json' \
                        -H 'Content-Type: application/json' \
                        -H 'X-API-KEY: sk_621d88dfcc31a1d3efa89a2873d394563f53bfd6fe1c7aec2ffd22e45d7b1d44' \
                        -d '{"sources": ["finance.yahoo.com"],
                        "excludeSources": ["www.aljazeera.com"],
                        "countries": ["IN","US"],
                        "from": "2025-11-09T22:06",
                        "to": "2025-11-10T22:06",
                        "language": "en",
                        "pageSize": "2",
                        "page": "1",
                        "orderBy": "createdAt",
                        "order": "ASC"}'"


        example response:
        {
  "status": "ok",
  "page": 1,
  "pageSize": 2,
  "articles": [
    {
      "link": "https://finance.yahoo.com/news/crypto-prices-rise-trump-announces-143034095.html",
      "source": "finance.yahoo.com",
      "title": "Crypto Prices Rise as Trump Announces ‘At Least’ $2K Tariff Dividend Per American",
      "summary": "The rally comes after a broader weekly slump, with the CoinDesk 20 (CD20) index recovering from a near 15% drawdown over the week.",
      "publishDate": "2025-11-09T14:30:34.000Z",
      "language": "en",
      "createdAt": "2025-11-09T23:12:47.718Z",
      "images": [
        "https://s.yimg.com/uu/api/res/1.2/JoT0qWEdMlpnGzGSEnxZfQ--~B/aD0xMDgwO3c9MTkyMDthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/coindesk_75/261ebe6bf74658e768f8d4fdb1fa7519.cf.webp"
      ]
    },
    {
      "link": "https://finance.yahoo.com/news/bitcoins-100k-heres-why-btc-151420905.html",
      "source": "finance.yahoo.com",
      "title": "Bitcoin's $100K Question: Here's Why BTC, XRP, SOL May Surge This Week",
      "summary": "Bitcoin has rebounded above $103,000, lifting altcoins.",
      "publishDate": "2025-11-09T15:14:20.000Z",
      "language": "en",
      "createdAt": "2025-11-09T23:14:55.119Z",
      "images": [
        "https://s.yimg.com/uu/api/res/1.2/KGylyZWM_O6wECjX5My03g--~B/aD0xMDgwO3c9MTYxOTthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/coindesk_75/b5e33b7a7fd6adf375da228ed5e001d4.cf.webp"
      ]
    }
  ]
}
        """
        url = self.fetch_news_post_url
        api_key = self.api_key

        json_body = {   
                        "sources": sources,
                        "excludeSources": exclude_sources,
                        "countries": countries,
                        "from": from_date,
                        "to": to_date,
                        "language": language,
                        "pageSize": page_size,
                        "page": page_count,
                        "orderBy": order_by,
                        "order": order
                    }
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-API-KEY": api_key
        }

        response = requests.post(url, json=json_body, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return data.get("articles", [])
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return []

    def fetch_news_sources_get(self, language="en"):
        """
        Fetch news sources using GET request.

        request url example:
        curl -X 'GET' 'https://api.finlight.me/v2/sources' \
                -H 'accept: */*' \
                -H 'X-API-KEY: sk_621d88dfcc31a1d3efa89a2873d394563f53bfd6fe1c7aec2ffd22e45d7b1d44'
        
        `example response:
        [
                {
                    "domain": "abcnews.go.com",
                    "isDefaultSource": true
                },
                {
                    "domain": "apnews.com",
                    "isDefaultSource": true
                },
                {
                    "domain": "asia.nikkei.com",
                    "isDefaultSource": true
                },
                {
                    "domain": "b2b.economictimes.indiatimes.com",
                    "isDefaultSource": false
                },
                {
                    "domain": "www.theguardian.com",
                    "isDefaultSource": true
                },
                {
                    "domain": "www.thenationalnews.com",
                    "isDefaultSource": false
                },
                {
                    "domain": "www.thestreet.com",
                    "isDefaultSource": false
                },
                {
                    "domain": "www.washingtonpost.com",
                    "isDefaultSource": true
                },
                {
                    "domain": "www.wsj.com",
                    "isDefaultSource": true
                },
                {
                    "domain": "www.yahoo.com",
                    "isDefaultSource": true
                }
        ]        
        """

        url = self.fetch_news_sources_get_url
        api_key = self.api_key

        headers = {
            "accept": "*/*",
            "X-API-KEY": api_key
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return []
        

if __name__ == "__main__":
    news_fetcher = NewsFetcher()

    # Example usage of fetch_news_post
    articles = news_fetcher.fetch_news_post(
        query="cryptocurrency",
        sources=["finance.yahoo.com"],
        exclude_sources=["www.aljazeera.com"],
        countries=["IN", "US"],
        from_date="2025-11-09T22:06",
        to_date="2025-11-10T22:06",
        language="en",
        page_size=2,
        page_count=1,
        order_by="createdAt",
        order="DESC"
    )
    print("Fetched Articles:")
    for article in articles:
        print(article)

    # Example usage of fetch_news_sources_get
    sources = news_fetcher.fetch_news_sources_get(language="en")
    print("\nFetched News Sources:")
    for source in sources:
        print(source)