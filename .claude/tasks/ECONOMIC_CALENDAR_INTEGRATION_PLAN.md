# 📅 Economic Calendar Integration Plan

## Current State Analysis

### ✅ What We Have
1. **Emergency Risk Manager** - Has circuit breaker mechanism for halting trades
2. **News Sentiment Analysis** - Fetches news but doesn't filter economic events  
3. **API Keys Available**:
   - Alpha Vantage (has economic indicators API)
   - Polygon (has market holidays/events)
   - NewsAPI (could filter for central bank news)

### ❌ What's Missing
1. No economic calendar monitoring
2. No event impact classification (high/medium/low)
3. No pre-event trading pause mechanism
4. No post-event volatility assessment

## Implementation Plan

### Phase 1: Economic Calendar Data Source

#### Option A: Alpha Vantage Economic Calendar
```python
# Use existing Alpha Vantage key
# Endpoints: FEDERAL_FUNDS_RATE, CPI, GDP, etc.
```

#### Option B: Free Economic Calendar APIs
- **ForexFactory API** (scraping required)
- **Investing.com Economic Calendar** (unofficial API)
- **TradingEconomics** (free tier available)
- **FXStreet Economic Calendar**

#### Option C: Perplexity Integration
- Real-time event context and analysis
- Pre-event risk assessment
- Post-event impact analysis

### Phase 2: Core Implementation

#### 1. Economic Event Monitor (`core/economic_calendar_monitor.py`)
```python
class EconomicCalendarMonitor:
    def __init__(self):
        self.high_impact_events = [
            "Interest Rate Decision",
            "FOMC Meeting",
            "ECB Meeting", 
            "BOE Meeting",
            "NFP (Non-Farm Payrolls)",
            "CPI Release",
            "GDP Release",
            "Central Bank Speech"
        ]
        
    def fetch_calendar_events(self, days_ahead=7):
        """Fetch upcoming economic events"""
        
    def classify_event_impact(self, event):
        """Classify as HIGH/MEDIUM/LOW impact"""
        
    def should_pause_trading(self, event):
        """Determine if trading should pause"""
        
    def get_pause_window(self, event):
        """Return pause duration (before/after event)"""
```

#### 2. Integration with Emergency Risk Manager
```python
# In emergency_risk_manager.py
def check_economic_events(self):
    """Check for upcoming high-impact events"""
    events = self.calendar_monitor.get_upcoming_events()
    
    for event in events:
        if event['impact'] == 'HIGH':
            pause_start = event['time'] - timedelta(hours=2)
            pause_end = event['time'] + timedelta(hours=2)
            
            if pause_start <= datetime.now() <= pause_end:
                self._trigger_event_pause(event)
                return False, f"Trading paused: {event['name']}"
```

#### 3. Configuration in `global.yaml`
```yaml
economic_calendar:
  enabled: true
  data_source: "alpha_vantage"  # or "perplexity", "tradingeconomics"
  
  pause_settings:
    high_impact_pause: true
    pause_before_minutes: 120  # 2 hours before
    pause_after_minutes: 120   # 2 hours after
    
  high_impact_events:
    - "Interest Rate Decision"
    - "FOMC Meeting"
    - "ECB Meeting"
    - "BOE Meeting"
    - "NFP"
    - "CPI"
    - "GDP"
    
  markets_affected:
    BOE:
      - "FTSE"
      - "GBP"
    ECB:
      - "DAX"
      - "EUR"
    FOMC:
      - "US500"
      - "USD"
```

### Phase 3: Event-Specific Strategies

#### Pre-Event Actions
1. Close all positions 2 hours before high-impact events
2. Reduce position sizes for medium-impact events
3. Tighten stop losses
4. Disable new trade entries

#### Post-Event Actions
1. Wait for volatility to normalize
2. Analyze event outcome vs expectations
3. Adjust trading parameters based on new market regime
4. Resume trading with reduced size initially

### Phase 4: Implementation Steps

1. **Create Economic Calendar Monitor**
   - Fetch calendar data
   - Parse and classify events
   - Store in database

2. **Integrate with Risk Manager**
   - Add event checking to trade validation
   - Implement pause/resume mechanism
   - Log all event-based actions

3. **Add Dashboard/Reporting**
   - Show upcoming events
   - Display pause windows
   - Track event impact on P&L

4. **Testing**
   - Backtest with historical events
   - Simulate event scenarios
   - Validate pause/resume logic

## Required Resources

### APIs Needed (Choose One)
1. **Alpha Vantage** (Already have key: WB87DUF9M5MPKMTM)
   - Pros: Already integrated, reliable
   - Cons: Limited economic calendar data

2. **TradingEconomics**
   - Pros: Comprehensive calendar, free tier
   - Cons: Need new API key

3. **Perplexity API** 
   - Pros: AI-powered analysis, real-time context
   - Cons: Need API key, potential costs

### Estimated Development Time
- Phase 1: 2-3 hours (API integration)
- Phase 2: 3-4 hours (Core implementation)
- Phase 3: 2-3 hours (Strategy adjustments)
- Phase 4: 2-3 hours (Testing & validation)

**Total: ~10-13 hours**

## Benefits
1. **Risk Reduction**: Avoid trading during high-volatility events
2. **Capital Preservation**: Prevent losses from unexpected announcements
3. **Better Timing**: Resume trading when conditions normalize
4. **Informed Decisions**: Know when major events are coming

## Next Steps
1. Choose data source (Alpha Vantage vs Perplexity vs other)
2. Implement basic calendar fetching
3. Create pause mechanism
4. Test with historical events
5. Deploy to production

---

Would you like me to proceed with implementing this economic calendar integration? I recommend starting with Alpha Vantage (since we have the API key) and potentially adding Perplexity for enhanced event analysis.