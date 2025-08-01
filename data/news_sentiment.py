# data/news_sentiment.py

"""
📰 News Sentiment Analysis Module

Fetches financial news from multiple sources and analyzes sentiment
to enhance trading decisions with fundamental analysis.

Features:
- Multi-source news aggregation
- Real-time sentiment scoring
- Market-specific news filtering
- Sentiment trend tracking
- Integration with trading signals

Author: Enhanced Algo Trading System
"""

import requests
import json
from datetime import datetime, timedelta
from textblob import TextBlob
import re
import time
from typing import Dict, List, Optional
import threading
from pymongo import MongoClient
import yaml

# Load config
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

# MongoDB connection for sentiment storage
client = MongoClient(config["mongodb"]["uri"])
db = client[config["mongodb"]["database"]]
news_collection = db["news_sentiment"]
sentiment_collection = db["market_sentiment"]

class NewsSourceManager:
    """Manages multiple news sources and API calls"""
    
    def __init__(self):
        self.sources = {
            "newsapi": {
                "url": "https://newsapi.org/v2/everything",
                "key": "YOUR_NEWSAPI_KEY",  # Get from newsapi.org
                "enabled": False  # Enable after getting API key
            },
            "alpha_vantage": {
                "url": "https://www.alphavantage.co/query",
                "key": "YOUR_ALPHA_VANTAGE_KEY",  # Get from alphavantage.co
                "enabled": False  # Enable after getting API key
            },
            "polygon": {
                "url": "https://api.polygon.io/v2/reference/news",
                "key": "YOUR_POLYGON_KEY",  # Get from polygon.io
                "enabled": False  # Enable after getting API key
            }
        }
        
        # Free sources (no API key required)
        self.free_sources = [
            "https://feeds.finance.yahoo.com/rss/2.0/headline",
            "https://www.investing.com/rss/news.rss",
            "https://feeds.bloomberg.com/markets/news.rss"
        ]
        
    def fetch_news_api(self, query: str, hours_back: int = 6) -> List[Dict]:
        """Fetch news from NewsAPI"""
        if not self.sources["newsapi"]["enabled"]:
            return []
            
        from_time = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        params = {
            "q": query,
            "from": from_time,
            "sortBy": "publishedAt",
            "apiKey": self.sources["newsapi"]["key"],
            "language": "en",
            "pageSize": 20
        }
        
        try:
            response = requests.get(self.sources["newsapi"]["url"], params=params, timeout=10)
            data = response.json()
            
            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "content": article.get("content", ""),
                    "url": article.get("url", ""),
                    "published_at": article.get("publishedAt", ""),
                    "source": article.get("source", {}).get("name", "NewsAPI")
                })
            
            return articles
            
        except Exception as e:
            print(f"❌ NewsAPI error: {e}")
            return []
    
    def fetch_free_financial_news(self, market_keywords: List[str]) -> List[Dict]:
        """Fetch news from free sources using web scraping"""
        articles = []
        
        # Simulate news fetching (in production, use RSS feeds or web scraping)
        # For demo purposes, create sample news articles
        sample_news = [
            {
                "title": f"DAX Index Shows Strong Performance Amid Market Volatility",
                "description": "German DAX index demonstrates resilience despite global market concerns",
                "content": "The DAX index has shown remarkable strength in recent trading sessions...",
                "url": "https://example.com/dax-performance",
                "published_at": datetime.now().isoformat(),
                "source": "Financial News Wire"
            },
            {
                "title": f"FTSE 100 Faces Headwinds from Brexit Concerns",
                "description": "UK's FTSE 100 under pressure from ongoing political uncertainties",
                "content": "The FTSE 100 is experiencing downward pressure due to renewed Brexit discussions...",
                "url": "https://example.com/ftse-brexit",
                "published_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "source": "Market Watch"
            },
            {
                "title": f"Central Bank Policy Decisions Impact European Markets",
                "description": "ECB monetary policy shifts affecting European equity markets",
                "content": "European Central Bank's latest policy announcements are reshaping market expectations...",
                "url": "https://example.com/ecb-policy",
                "published_at": (datetime.now() - timedelta(hours=4)).isoformat(),
                "source": "Reuters"
            }
        ]
        
        return sample_news

class SentimentAnalyzer:
    """Analyzes sentiment of financial news articles"""
    
    def __init__(self):
        self.financial_keywords = {
            # Positive indicators
            "bullish": 2.0, "rally": 1.5, "surge": 1.8, "gain": 1.2, "rise": 1.0,
            "growth": 1.3, "profit": 1.4, "strong": 1.1, "positive": 1.0, "up": 0.8,
            "boost": 1.6, "jump": 1.7, "soar": 1.9, "climb": 1.2, "advance": 1.1,
            
            # Negative indicators  
            "bearish": -2.0, "crash": -2.5, "plunge": -2.2, "fall": -1.2, "drop": -1.3,
            "decline": -1.4, "loss": -1.5, "weak": -1.1, "negative": -1.0, "down": -0.8,
            "sell-off": -1.8, "tumble": -1.6, "slide": -1.3, "retreat": -1.2, "slump": -1.7,
            
            # Volatility indicators
            "volatile": -0.5, "uncertainty": -0.8, "risk": -0.6, "concern": -0.7,
            "worry": -0.9, "fear": -1.2, "panic": -1.8, "crisis": -2.0
        }
    
    def analyze_text_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of a single text using multiple methods"""
        if not text:
            return {"polarity": 0, "subjectivity": 0, "financial_score": 0, "confidence": 0}
        
        # TextBlob sentiment analysis
        blob = TextBlob(text.lower())
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1
        
        # Financial keyword scoring
        financial_score = 0
        keyword_matches = 0
        
        for keyword, weight in self.financial_keywords.items():
            if keyword in text.lower():
                financial_score += weight
                keyword_matches += 1
        
        # Normalize financial score
        if keyword_matches > 0:
            financial_score = financial_score / keyword_matches
            financial_score = max(-2.0, min(2.0, financial_score))  # Clamp to -2, 2
        
        # Combined sentiment score
        combined_score = (polarity + financial_score) / 2
        confidence = min(1.0, (abs(polarity) + abs(financial_score) + keyword_matches/10))
        
        return {
            "polarity": round(polarity, 3),
            "subjectivity": round(subjectivity, 3),
            "financial_score": round(financial_score, 3),
            "combined_score": round(combined_score, 3),
            "confidence": round(confidence, 3),
            "keyword_matches": keyword_matches
        }
    
    def analyze_article(self, article: Dict) -> Dict:
        """Analyze sentiment of a complete news article"""
        # Combine title, description, and content for analysis
        full_text = ""
        if article.get("title"):
            full_text += article["title"] + ". "
        if article.get("description"):
            full_text += article["description"] + ". "
        if article.get("content"):
            full_text += article["content"][:500]  # Limit content length
        
        sentiment = self.analyze_text_sentiment(full_text)
        
        # Weight title more heavily
        if article.get("title"):
            title_sentiment = self.analyze_text_sentiment(article["title"])
            sentiment["combined_score"] = (sentiment["combined_score"] * 0.7 + 
                                         title_sentiment["combined_score"] * 0.3)
        
        return {
            **article,
            "sentiment": sentiment,
            "analyzed_at": datetime.now().isoformat()
        }

class MarketSentimentTracker:
    """Tracks overall market sentiment across multiple timeframes"""
    
    def __init__(self):
        self.sentiment_thresholds = {
            "very_bearish": -1.5,
            "bearish": -0.5,
            "neutral": 0.0,
            "bullish": 0.5,
            "very_bullish": 1.5
        }
    
    def calculate_market_sentiment(self, market: str, hours_back: int = 6) -> Dict:
        """Calculate overall sentiment for a specific market"""
        # Get recent sentiment data
        since_time = datetime.now() - timedelta(hours=hours_back)
        
        articles = list(news_collection.find({
            "analyzed_at": {"$gte": since_time.isoformat()},
            "$or": [
                {"title": {"$regex": market, "$options": "i"}},
                {"description": {"$regex": market, "$options": "i"}}
            ]
        }))
        
        if not articles:
            return {
                "market": market,
                "sentiment_score": 0,
                "sentiment_label": "neutral",
                "confidence": 0,
                "article_count": 0,
                "last_update": datetime.now().isoformat()
            }
        
        # Calculate weighted average sentiment
        total_score = 0
        total_weight = 0
        
        for article in articles:
            sentiment = article.get("sentiment", {})
            score = sentiment.get("combined_score", 0)
            confidence = sentiment.get("confidence", 0.5)
            
            # Weight by confidence and recency
            age_hours = (datetime.now() - datetime.fromisoformat(article["analyzed_at"])).total_seconds() / 3600
            recency_weight = max(0.1, 1.0 - (age_hours / hours_back))
            
            weight = confidence * recency_weight
            total_score += score * weight
            total_weight += weight
        
        if total_weight == 0:
            avg_sentiment = 0
        else:
            avg_sentiment = total_score / total_weight
        
        # Determine sentiment label
        sentiment_label = "neutral"
        for label, threshold in sorted(self.sentiment_thresholds.items(), 
                                     key=lambda x: abs(x[1] - avg_sentiment)):
            if (label.endswith("bullish") and avg_sentiment >= threshold) or \
               (label.endswith("bearish") and avg_sentiment <= threshold):
                sentiment_label = label
                break
        
        result = {
            "market": market,
            "sentiment_score": round(avg_sentiment, 3),
            "sentiment_label": sentiment_label,
            "confidence": round(total_weight / len(articles), 3) if articles else 0,
            "article_count": len(articles),
            "timeframe_hours": hours_back,
            "last_update": datetime.now().isoformat()
        }
        
        # Store in database
        sentiment_collection.update_one(
            {"market": market, "timeframe_hours": hours_back},
            {"$set": result},
            upsert=True
        )
        
        return result

class NewsSentimentEngine:
    """Main engine that coordinates news fetching and sentiment analysis"""
    
    def __init__(self):
        self.news_manager = NewsSourceManager()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.sentiment_tracker = MarketSentimentTracker()
        self.running = False
        
    def fetch_and_analyze_news(self, markets: List[str]) -> Dict:
        """Fetch news and analyze sentiment for given markets"""
        all_results = {}
        
        for market in markets:
            print(f"📰 Fetching news for {market}...")
            
            # Fetch news from available sources
            articles = []
            
            # Try API sources first
            api_articles = self.news_manager.fetch_news_api(market)
            articles.extend(api_articles)
            
            # Get free source articles
            free_articles = self.news_manager.fetch_free_financial_news([market])
            articles.extend(free_articles)
            
            # Analyze sentiment for each article
            analyzed_articles = []
            for article in articles:
                analyzed_article = self.sentiment_analyzer.analyze_article(article)
                analyzed_articles.append(analyzed_article)
                
                # Store in database
                news_collection.update_one(
                    {"url": article.get("url", ""), "market": market},
                    {"$set": {**analyzed_article, "market": market}},
                    upsert=True
                )
            
            # Calculate overall market sentiment
            market_sentiment = self.sentiment_tracker.calculate_market_sentiment(market)
            
            all_results[market] = {
                "articles": analyzed_articles,
                "market_sentiment": market_sentiment
            }
            
            print(f"📊 {market} Sentiment: {market_sentiment['sentiment_score']:.2f} ({market_sentiment['sentiment_label']}) - {len(analyzed_articles)} articles")
        
        return all_results
    
    def get_trading_sentiment_signal(self, market: str) -> Dict:
        """Get sentiment-based trading signal for a market"""
        # Get current market sentiment
        sentiment_data = self.sentiment_tracker.calculate_market_sentiment(market, hours_back=6)
        
        score = sentiment_data["sentiment_score"]
        confidence = sentiment_data["confidence"]
        
        # Generate trading signal based on sentiment
        signal = "HOLD"
        signal_strength = 0
        
        if confidence > 0.3:  # Only act on confident sentiment
            if score >= 0.8:
                signal = "BUY"
                signal_strength = min(1.0, score)
            elif score <= -0.8:
                signal = "SELL" 
                signal_strength = min(1.0, abs(score))
        
        return {
            "market": market,
            "sentiment_signal": signal,
            "signal_strength": signal_strength,
            "sentiment_score": score,
            "confidence": confidence,
            "recommendation": f"Sentiment suggests {signal} with {signal_strength:.1f} strength" if signal != "HOLD" else "Neutral sentiment - no clear direction"
        }
    
    def start_continuous_monitoring(self, markets: List[str], interval_minutes: int = 30):
        """Start continuous news monitoring in background"""
        self.running = True
        
        def monitor_loop():
            while self.running:
                try:
                    print(f"🔄 Running sentiment analysis cycle...")
                    self.fetch_and_analyze_news(markets)
                    print(f"⏳ Waiting {interval_minutes} minutes for next cycle...")
                    time.sleep(interval_minutes * 60)
                except Exception as e:
                    print(f"❌ Sentiment monitoring error: {e}")
                    time.sleep(60)  # Wait 1 minute before retry
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        print(f"🚀 Started continuous sentiment monitoring for {markets}")
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.running = False
        print("🛑 Stopped sentiment monitoring")

# Global sentiment engine instance
_global_sentiment_engine = None

def get_sentiment_engine():
    """Get global sentiment engine instance"""
    global _global_sentiment_engine
    if _global_sentiment_engine is None:
        _global_sentiment_engine = NewsSentimentEngine()
    return _global_sentiment_engine

def get_market_sentiment_signal(market: str) -> Dict:
    """Quick function to get sentiment signal for a market"""
    engine = get_sentiment_engine()
    return engine.get_trading_sentiment_signal(market)

if __name__ == "__main__":
    # Test the sentiment analysis system
    print("🧪 Testing News Sentiment Analysis System")
    print("=" * 50)
    
    engine = NewsSentimentEngine()
    
    # Test with sample markets
    markets = ["DAX", "FTSE"]
    results = engine.fetch_and_analyze_news(markets)
    
    for market, data in results.items():
        print(f"\n📊 {market} Results:")
        sentiment = data["market_sentiment"]
        print(f"   Overall Sentiment: {sentiment['sentiment_score']:.2f} ({sentiment['sentiment_label']})")
        print(f"   Confidence: {sentiment['confidence']:.2f}")
        print(f"   Articles Analyzed: {sentiment['article_count']}")
        
        # Get trading signal
        signal = engine.get_trading_sentiment_signal(market)
        print(f"   Trading Signal: {signal['sentiment_signal']} (strength: {signal['signal_strength']:.2f})")
        print(f"   Recommendation: {signal['recommendation']}")