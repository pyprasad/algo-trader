#!/usr/bin/env python3
"""
📅 Economic Calendar Data Fetcher

Fetches economic events from multiple sources:
- Alpha Vantage (for US economic indicators)
- ForexFactory (for comprehensive global calendar)
- JBlanked API (reliable alternative to scraping)

Author: Economic Calendar Integration System
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import logging
from dataclasses import dataclass
# Optional imports for web scraping
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
import pandas as pd
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EconomicEvent:
    """Data class for economic events"""
    event_date: datetime
    event_name: str
    currency: str
    impact_level: str  # HIGH, MEDIUM, LOW
    actual_value: Optional[Union[str, float]] = None
    forecast_value: Optional[Union[str, float]] = None
    previous_value: Optional[Union[str, float]] = None
    source: str = "unknown"
    description: str = ""

class AlphaVantageEconomicFetcher:
    """Fetches economic data from Alpha Vantage API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.rate_limit_delay = 12  # 12 seconds between requests (5 requests/minute)
        
    def _make_request(self, function: str, **params) -> Dict:
        """Make API request with rate limiting"""
        
        url_params = {
            'function': function,
            'apikey': self.api_key,
            **params
        }
        
        try:
            response = requests.get(self.base_url, params=url_params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API error
            if "Error Message" in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return {}
            
            if "Note" in data and "API call frequency" in data["Note"]:
                logger.warning("Alpha Vantage rate limit hit, waiting...")
                time.sleep(60)  # Wait 1 minute if rate limited
                return self._make_request(function, **params)
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Alpha Vantage API request failed: {e}")
            return {}
    
    def fetch_economic_indicators(self, days_ahead: int = 30) -> List[EconomicEvent]:
        """
        Fetch economic indicators from Alpha Vantage
        Note: Alpha Vantage provides historical data, not future calendar events
        """
        events = []
        
        # List of economic functions to fetch
        indicators = [
            ('FEDERAL_FUNDS_RATE', 'Federal Funds Rate', 'USD', 'HIGH'),
            ('CPI', 'Consumer Price Index', 'USD', 'HIGH'),
            ('UNEMPLOYMENT', 'Unemployment Rate', 'USD', 'HIGH'),
            ('NONFARM_PAYROLL', 'Non-Farm Payroll', 'USD', 'HIGH'),
            ('REAL_GDP', 'GDP', 'USD', 'HIGH'),
            ('TREASURY_YIELD', 'Treasury Yield', 'USD', 'MEDIUM'),
            ('INFLATION', 'Inflation', 'USD', 'HIGH'),
            ('RETAIL_SALES', 'Retail Sales', 'USD', 'MEDIUM')
        ]
        
        for function, name, currency, impact in indicators:
            try:
                data = self._make_request(function, interval='monthly')
                
                if 'data' in data:
                    # Process the most recent data point
                    recent_data = data['data'][:3]  # Get last 3 months
                    
                    for item in recent_data:
                        try:
                            event_date = datetime.strptime(item.get('date', ''), '%Y-%m-%d')
                            
                            event = EconomicEvent(
                                event_date=event_date,
                                event_name=name,
                                currency=currency,
                                impact_level=impact,
                                actual_value=item.get('value'),
                                source='alpha_vantage',
                                description=f"Latest {name} data from Alpha Vantage"
                            )
                            
                            events.append(event)
                            
                        except (ValueError, KeyError) as e:
                            logger.warning(f"Error parsing {name} data: {e}")
                            continue
                            
                logger.info(f"Fetched {name} data from Alpha Vantage")
                
            except Exception as e:
                logger.error(f"Error fetching {name} from Alpha Vantage: {e}")
                continue
        
        logger.info(f"Alpha Vantage fetched {len(events)} economic indicators")
        return events

class ForexFactoryFetcher:
    """Fetches economic calendar from ForexFactory"""
    
    def __init__(self, username: str = None, password: str = None):
        self.username = username
        self.password = password
        self.base_url = "https://www.forexfactory.com"
        self.session = requests.Session()
        
        # Set headers to mimic browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def login(self) -> bool:
        """Login to ForexFactory if credentials provided"""
        if not self.username or not self.password:
            logger.info("No ForexFactory credentials provided, using guest access")
            return True
        
        try:
            # Get login page
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url)
            
            if response.status_code != 200:
                logger.error(f"Failed to access login page: {response.status_code}")
                return False
            
            # Parse login form (simplified - may need CSRF tokens)
            login_data = {
                'username': self.username,
                'password': self.password,
                'remember_me': '1'
            }
            
            # Submit login
            response = self.session.post(login_url, data=login_data)
            
            if "logout" in response.text.lower():
                logger.info("Successfully logged into ForexFactory")
                return True
            else:
                logger.warning("ForexFactory login may have failed, continuing as guest")
                return True
                
        except Exception as e:
            logger.error(f"ForexFactory login error: {e}")
            return True  # Continue as guest
    
    def fetch_calendar_events(self, days_ahead: int = 7) -> List[EconomicEvent]:
        """Fetch economic calendar events from ForexFactory"""
        
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available - ForexFactory scraping disabled")
            return []
        
        if not self.login():
            logger.error("Failed to login to ForexFactory")
            return []
        
        events = []
        
        try:
            # Generate date range
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days_ahead)
            
            for single_date in pd.date_range(start_date, end_date):
                date_str = single_date.strftime('%Y-%m-%d')
                calendar_url = f"{self.base_url}/calendar?day={date_str}"
                
                try:
                    response = self.session.get(calendar_url, timeout=30)
                    if response.status_code != 200:
                        logger.warning(f"Failed to fetch calendar for {date_str}: {response.status_code}")
                        continue
                    
                    # Parse HTML
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find calendar table
                    calendar_table = soup.find('table', class_='calendar__table')
                    if not calendar_table:
                        logger.warning(f"No calendar table found for {date_str}")
                        continue
                    
                    # Parse events
                    day_events = self._parse_calendar_table(calendar_table, single_date.date())
                    events.extend(day_events)
                    
                    logger.info(f"Fetched {len(day_events)} events for {date_str}")
                    
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error fetching calendar for {date_str}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in ForexFactory calendar fetch: {e}")
        
        logger.info(f"ForexFactory fetched {len(events)} total events")
        return events
    
    def _parse_calendar_table(self, table, event_date) -> List[EconomicEvent]:
        """Parse ForexFactory calendar table"""
        events = []
        
        try:
            rows = table.find_all('tr', class_='calendar__row')
            
            for row in rows:
                try:
                    # Extract event details
                    time_cell = row.find('td', class_='calendar__time')
                    currency_cell = row.find('td', class_='calendar__currency')
                    impact_cell = row.find('td', class_='calendar__impact')
                    event_cell = row.find('td', class_='calendar__event')
                    actual_cell = row.find('td', class_='calendar__actual')
                    forecast_cell = row.find('td', class_='calendar__forecast')
                    previous_cell = row.find('td', class_='calendar__previous')
                    
                    if not all([currency_cell, event_cell]):
                        continue
                    
                    # Extract data
                    currency = currency_cell.get_text(strip=True)
                    event_name = event_cell.get_text(strip=True)
                    
                    # Skip if not relevant currency
                    if currency not in ['USD', 'EUR', 'GBP']:
                        continue
                    
                    # Determine impact level
                    impact_level = 'LOW'
                    if impact_cell:
                        impact_spans = impact_cell.find_all('span', class_='calendar__impact-icon')
                        if len(impact_spans) >= 3:
                            impact_level = 'HIGH'
                        elif len(impact_spans) >= 2:
                            impact_level = 'MEDIUM'
                    
                    # Parse time
                    event_time = datetime.combine(event_date, datetime.min.time())
                    if time_cell:
                        time_text = time_cell.get_text(strip=True)
                        if time_text and ':' in time_text:
                            try:
                                time_parts = time_text.split(':')
                                hour = int(time_parts[0])
                                minute = int(time_parts[1][:2])  # Handle AM/PM
                                event_time = datetime.combine(event_date, datetime.min.time().replace(hour=hour, minute=minute))
                            except:
                                pass
                    
                    # Extract values
                    actual = actual_cell.get_text(strip=True) if actual_cell else None
                    forecast = forecast_cell.get_text(strip=True) if forecast_cell else None
                    previous = previous_cell.get_text(strip=True) if previous_cell else None
                    
                    event = EconomicEvent(
                        event_date=event_time,
                        event_name=event_name,
                        currency=currency,
                        impact_level=impact_level,
                        actual_value=actual,
                        forecast_value=forecast,
                        previous_value=previous,
                        source='forexfactory',
                        description=f"ForexFactory: {event_name}"
                    )
                    
                    events.append(event)
                    
                except Exception as e:
                    logger.warning(f"Error parsing ForexFactory row: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing ForexFactory table: {e}")
        
        return events

class JBlankedApiFetcher:
    """Alternative ForexFactory data via JBlanked API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://www.jblanked.com/api/news-calendar"
        self.headers = {
            'Authorization': f'Bearer {api_key}' if api_key else '',
            'Accept': 'application/json',
            'User-Agent': 'Economic Calendar Bot 1.0'
        }
    
    def fetch_calendar_events(self, days_ahead: int = 7) -> List[EconomicEvent]:
        """Fetch events from JBlanked News Calendar API"""
        
        if not self.api_key:
            logger.warning("No JBlanked API key provided")
            return []
        
        events = []
        
        try:
            # Fetch today's events
            today_url = f"{self.base_url}/today"
            response = requests.get(today_url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                events.extend(self._parse_jblanked_events(data))
            
            # Fetch week's events
            week_url = f"{self.base_url}/week"
            response = requests.get(week_url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                events.extend(self._parse_jblanked_events(data))
            
            # Rate limiting (1 request per second)
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"JBlanked API error: {e}")
        
        logger.info(f"JBlanked API fetched {len(events)} events")
        return events
    
    def _parse_jblanked_events(self, data: Dict) -> List[EconomicEvent]:
        """Parse JBlanked API response"""
        events = []
        
        try:
            if 'events' in data:
                for event_data in data['events']:
                    try:
                        event_date = datetime.strptime(event_data.get('date', ''), '%Y-%m-%d %H:%M:%S')
                        
                        event = EconomicEvent(
                            event_date=event_date,
                            event_name=event_data.get('title', ''),
                            currency=event_data.get('currency', ''),
                            impact_level=event_data.get('impact', 'LOW').upper(),
                            actual_value=event_data.get('actual'),
                            forecast_value=event_data.get('forecast'),
                            previous_value=event_data.get('previous'),
                            source='jblanked',
                            description=event_data.get('description', '')
                        )
                        
                        events.append(event)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing JBlanked event: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error parsing JBlanked data: {e}")
        
        return events

class EconomicCalendarDataFetcher:
    """Main economic calendar data fetcher coordinator"""
    
    def __init__(self, config: Dict):
        """Initialize with configuration"""
        self.config = config
        self.fetchers = []
        
        # Initialize Alpha Vantage if configured
        alpha_config = config.get('alpha_vantage', {})
        if alpha_config.get('enabled', False) and alpha_config.get('key'):
            self.alpha_fetcher = AlphaVantageEconomicFetcher(alpha_config['key'])
            self.fetchers.append(('alpha_vantage', self.alpha_fetcher))
            logger.info("Alpha Vantage fetcher initialized")
        
        # Initialize ForexFactory if configured
        forex_config = config.get('forexfactory', {})
        if forex_config.get('enabled', False):
            username = forex_config.get('username')
            password = forex_config.get('password')
            self.forex_fetcher = ForexFactoryFetcher(username, password)
            self.fetchers.append(('forexfactory', self.forex_fetcher))
            logger.info("ForexFactory fetcher initialized")
        
        # Initialize JBlanked API if configured
        jblanked_config = config.get('jblanked', {})
        if jblanked_config.get('enabled', False) and jblanked_config.get('api_key'):
            self.jblanked_fetcher = JBlankedApiFetcher(jblanked_config['api_key'])
            self.fetchers.append(('jblanked', self.jblanked_fetcher))
            logger.info("JBlanked API fetcher initialized")
    
    def fetch_all_events(self, days_ahead: int = 7) -> List[EconomicEvent]:
        """Fetch events from all configured sources"""
        all_events = []
        
        for source_name, fetcher in self.fetchers:
            try:
                logger.info(f"Fetching events from {source_name}...")
                
                if source_name == 'alpha_vantage':
                    events = fetcher.fetch_economic_indicators(days_ahead)
                else:
                    events = fetcher.fetch_calendar_events(days_ahead)
                
                for event in events:
                    event.source = source_name
                
                all_events.extend(events)
                logger.info(f"Fetched {len(events)} events from {source_name}")
                
            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
                continue
        
        # Deduplicate and sort events
        unique_events = self._deduplicate_events(all_events)
        unique_events.sort(key=lambda x: x.event_date)
        
        logger.info(f"Total unique events fetched: {len(unique_events)}")
        return unique_events
    
    def _deduplicate_events(self, events: List[EconomicEvent]) -> List[EconomicEvent]:
        """Remove duplicate events based on date, name, and currency"""
        seen = set()
        unique_events = []
        
        for event in events:
            # Create key for deduplication
            key = (
                event.event_date.date(),
                event.event_name.lower().strip(),
                event.currency
            )
            
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        return unique_events

def test_economic_fetcher():
    """Test function for the economic calendar fetcher"""
    print("🧪 Testing Economic Calendar Data Fetcher")
    print("=" * 50)
    
    # Test configuration
    config = {
        'alpha_vantage': {
            'enabled': True,
            'key': 'WB87DUF9M5MPKMTM'
        },
        'forexfactory': {
            'enabled': True,
            'username': 'yuganp',
            'password': 'Testing@123'
        }
    }
    
    fetcher = EconomicCalendarDataFetcher(config)
    events = fetcher.fetch_all_events(days_ahead=7)
    
    print(f"\n📅 Fetched {len(events)} economic events:")
    
    for event in events[:10]:  # Show first 10 events
        print(f"  📊 {event.event_date.strftime('%Y-%m-%d %H:%M')} | {event.currency} | {event.impact_level} | {event.event_name} | {event.source}")
    
    # Count by impact level
    high_impact = [e for e in events if e.impact_level == 'HIGH']
    medium_impact = [e for e in events if e.impact_level == 'MEDIUM'] 
    low_impact = [e for e in events if e.impact_level == 'LOW']
    
    print(f"\n📈 Impact Level Distribution:")
    print(f"   🔴 HIGH: {len(high_impact)} events")
    print(f"   🟡 MEDIUM: {len(medium_impact)} events")
    print(f"   🟢 LOW: {len(low_impact)} events")

if __name__ == "__main__":
    test_economic_fetcher()