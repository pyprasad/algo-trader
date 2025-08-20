# IG Markets API Reference

## Overview

This document provides comprehensive reference for integrating with the IG Markets API, including authentication, endpoints, data streaming, and error handling.

## API Architecture

### REST API
- **Base URL (Demo)**: `https://demo-api.ig.com/gateway/deal`
- **Base URL (Live)**: `https://api.ig.com/gateway/deal`
- **Protocol**: HTTPS
- **Format**: JSON
- **Version**: v3

### Streaming API (Lightstreamer)
- **URL (Demo)**: `https://demo-apd.marketdatasystems.com`
- **URL (Live)**: `https://apd.marketdatasystems.com`
- **Protocol**: WebSocket/HTTP Streaming
- **Real-time**: Market prices, account updates

## Authentication

### Initial Login

```python
# POST /session
headers = {
    'Content-Type': 'application/json',
    'X-IG-API-KEY': api_key,
    'Version': '3'
}

body = {
    'identifier': username,
    'password': password
}

response = requests.post(f"{base_url}/session", 
                         headers=headers, 
                         json=body)

# Response headers contain:
# CST: Client session token
# X-SECURITY-TOKEN: Security token for subsequent requests
```

### Session Management

```python
# All subsequent requests require:
headers = {
    'Content-Type': 'application/json',
    'X-IG-API-KEY': api_key,
    'CST': client_session_token,
    'X-SECURITY-TOKEN': security_token
}
```

### Logout

```python
# DELETE /session
response = requests.delete(f"{base_url}/session", headers=headers)
```

## Account Operations

### Get Accounts

```python
# GET /accounts
response = requests.get(f"{base_url}/accounts", headers=headers)

# Response:
{
    "accounts": [
        {
            "accountId": "ABC123",
            "accountName": "Demo Account",
            "accountType": "CFD",
            "preferred": true,
            "balance": {
                "balance": 10000.00,
                "deposit": 10000.00,
                "profitLoss": 0.00,
                "available": 10000.00
            }
        }
    ]
}
```

### Switch Account

```python
# PUT /session
body = {
    'accountId': 'ABC123'
}
response = requests.put(f"{base_url}/session", 
                        headers=headers, 
                        json=body)
```

### Get Account Activity

```python
# GET /history/activity
params = {
    'from': '2024-01-01T00:00:00',
    'to': '2024-01-31T23:59:59',
    'pageSize': 500
}
response = requests.get(f"{base_url}/history/activity", 
                       headers=headers, 
                       params=params)
```

## Market Data

### Search Markets

```python
# GET /markets
params = {
    'searchTerm': 'FTSE'
}
response = requests.get(f"{base_url}/markets", 
                       headers=headers, 
                       params=params)

# Response:
{
    "markets": [
        {
            "epic": "IX.D.FTSE.DAILY.IP",
            "instrumentName": "FTSE 100",
            "instrumentType": "INDICES",
            "expiry": "DFB",
            "marketStatus": "TRADEABLE"
        }
    ]
}
```

### Get Market Details

```python
# GET /markets/{epic}
epic = "IX.D.FTSE.DAILY.IP"
response = requests.get(f"{base_url}/markets/{epic}", headers=headers)

# Response:
{
    "instrument": {
        "epic": "IX.D.FTSE.DAILY.IP",
        "name": "FTSE 100",
        "type": "INDICES",
        "marketId": "FTSE",
        "newsCode": "UK100",
        "currency": "GBP",
        "minDealSize": {"unit": "POINTS", "value": 0.5},
        "maxDealSize": {"unit": "POINTS", "value": 500},
        "marginFactor": 5.0,
        "marginFactorUnit": "PERCENTAGE"
    },
    "snapshot": {
        "marketStatus": "TRADEABLE",
        "bid": 7500.5,
        "offer": 7501.5,
        "high": 7520.0,
        "low": 7480.0,
        "percentageChange": 0.5,
        "updateTime": "2024-01-15T14:30:00"
    },
    "dealingRules": {
        "minStopOrLimitDistance": {"unit": "POINTS", "value": 8},
        "minControlledRiskStopDistance": {"unit": "POINTS", "value": 10},
        "maxStopOrLimitDistance": {"unit": "PERCENTAGE", "value": 50}
    }
}
```

### Get Historical Prices

```python
# GET /prices/{epic}
params = {
    'resolution': 'MINUTE_5',  # 5-minute candles
    'max': 100,  # Number of data points
    'pageSize': 100
}
response = requests.get(f"{base_url}/prices/{epic}", 
                       headers=headers, 
                       params=params)

# Response:
{
    "prices": [
        {
            "snapshotTime": "2024-01-15T14:30:00",
            "openPrice": {"bid": 7500.0, "ask": 7501.0},
            "closePrice": {"bid": 7505.0, "ask": 7506.0},
            "highPrice": {"bid": 7510.0, "ask": 7511.0},
            "lowPrice": {"bid": 7495.0, "ask": 7496.0},
            "lastTradedVolume": 12500
        }
    ]
}
```

## Trading Operations

### Open Position

```python
# POST /positions/otc
body = {
    "epic": "IX.D.FTSE.DAILY.IP",
    "expiry": "DFB",
    "direction": "BUY",  # or "SELL"
    "size": 1,
    "orderType": "MARKET",
    "timeInForce": "FILL_OR_KILL",
    "guaranteedStop": False,
    "stopLevel": 7450,  # Stop loss level
    "stopDistance": None,  # Alternative to stopLevel
    "limitLevel": 7550,  # Take profit level
    "limitDistance": None,  # Alternative to limitLevel
    "forceOpen": True,
    "currencyCode": "GBP"
}

response = requests.post(f"{base_url}/positions/otc", 
                        headers=headers, 
                        json=body)

# Response:
{
    "dealReference": "DIAAAABCD1234567"
}

# Confirm deal
deal_ref = response.json()['dealReference']
confirm_response = requests.get(f"{base_url}/confirms/{deal_ref}", 
                               headers=headers)

# Confirmation response:
{
    "dealId": "DIAAAABCD1234567",
    "dealReference": "DIAAAABCD1234567",
    "dealStatus": "ACCEPTED",
    "status": "OPEN",
    "reason": "SUCCESS",
    "epic": "IX.D.FTSE.DAILY.IP",
    "direction": "BUY",
    "size": 1,
    "level": 7501.5,
    "stopLevel": 7450,
    "limitLevel": 7550,
    "guaranteedStop": false,
    "date": "2024-01-15T14:35:00"
}
```

### Update Position

```python
# PUT /positions/otc/{dealId}
body = {
    "stopLevel": 7460,  # New stop loss
    "limitLevel": 7540,  # New take profit
    "trailingStop": True,
    "trailingStopDistance": 20,
    "trailingStopIncrement": 1
}

response = requests.put(f"{base_url}/positions/otc/{deal_id}", 
                       headers=headers, 
                       json=body)
```

### Close Position

```python
# DELETE /positions/otc
body = {
    "dealId": "DIAAAABCD1234567",
    "direction": "SELL",  # Opposite of open direction
    "size": 1,
    "orderType": "MARKET",
    "timeInForce": "FILL_OR_KILL"
}

headers['_method'] = 'DELETE'  # Required for DELETE with body
response = requests.post(f"{base_url}/positions/otc", 
                        headers=headers, 
                        json=body)
```

### Get Open Positions

```python
# GET /positions
response = requests.get(f"{base_url}/positions", headers=headers)

# Response:
{
    "positions": [
        {
            "position": {
                "dealId": "DIAAAABCD1234567",
                "dealReference": "DIAAAABCD1234567",
                "createdDate": "2024-01-15T14:35:00",
                "createdDateUTC": "2024-01-15T14:35:00",
                "size": 1,
                "direction": "BUY",
                "limitLevel": 7550,
                "stopLevel": 7450,
                "currency": "GBP",
                "controlledRisk": false
            },
            "market": {
                "epic": "IX.D.FTSE.DAILY.IP",
                "instrumentName": "FTSE 100",
                "instrumentType": "INDICES",
                "expiry": "DFB",
                "marketStatus": "TRADEABLE",
                "bid": 7505.5,
                "offer": 7506.5,
                "percentageChange": 0.5,
                "updateTime": "14:40:00",
                "delayTime": 0,
                "streamingPricesAvailable": true,
                "scalingFactor": 1
            }
        }
    ]
}
```

## Working Orders

### Place Working Order

```python
# POST /workingorders/otc
body = {
    "epic": "IX.D.FTSE.DAILY.IP",
    "expiry": "DFB",
    "direction": "BUY",
    "size": 1,
    "level": 7490,  # Entry level for limit order
    "type": "LIMIT",  # or "STOP"
    "timeInForce": "GOOD_TILL_CANCELLED",
    "goodTillDate": None,
    "stopDistance": 50,
    "limitDistance": 100,
    "guaranteedStop": False,
    "currencyCode": "GBP"
}

response = requests.post(f"{base_url}/workingorders/otc", 
                        headers=headers, 
                        json=body)
```

### Get Working Orders

```python
# GET /workingorders
response = requests.get(f"{base_url}/workingorders", headers=headers)
```

### Delete Working Order

```python
# DELETE /workingorders/otc/{dealId}
response = requests.delete(f"{base_url}/workingorders/otc/{deal_id}", 
                          headers=headers)
```

## Streaming Data (Lightstreamer)

### Connection Setup

```python
from lightstreamer_client import LightstreamerClient, Subscription

# Create client
client = LightstreamerClient(
    base_url="https://demo-apd.marketdatasystems.com",
    adapter_set="DEFAULT"
)

# Set credentials
client.connectionDetails.setUser(account_id)
client.connectionDetails.setPassword(f"CST-{cst_token}|XST-{x_security_token}")

# Connect
client.connect()
```

### Subscribe to Market Data

```python
# Create subscription
subscription = Subscription(
    mode="MERGE",
    items=["MARKET:IX.D.FTSE.DAILY.IP"],
    fields=["BID", "OFFER", "HIGH", "LOW", "CHANGE", "UPDATE_TIME"]
)

# Add listener
class MarketListener:
    def on_item_update(self, update):
        print(f"Bid: {update.getValue('BID')}")
        print(f"Offer: {update.getValue('OFFER')}")
        
subscription.addListener(MarketListener())

# Subscribe
client.subscribe(subscription)
```

### Subscribe to Account Updates

```python
# Account subscription
account_subscription = Subscription(
    mode="MERGE",
    items=["ACCOUNT:{account_id}"],
    fields=["AVAILABLE_CASH", "PNL", "MARGIN", "FUNDS", "EQUITY"]
)

client.subscribe(account_subscription)
```

### Subscribe to Trade Updates

```python
# Trade subscription
trade_subscription = Subscription(
    mode="DISTINCT",
    items=["TRADE:{account_id}"],
    fields=["CONFIRMS", "OPU", "WOU"]
)

client.subscribe(trade_subscription)
```

## Error Handling

### HTTP Status Codes

| Code | Description | Action |
|------|-------------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Check request parameters |
| 401 | Unauthorized | Re-authenticate |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Verify endpoint/resource |
| 429 | Too Many Requests | Implement rate limiting |
| 500 | Internal Server Error | Retry with backoff |
| 503 | Service Unavailable | Wait and retry |

### Error Response Format

```json
{
    "errorCode": "error.invalid.daterange",
    "errorMessage": "Invalid date range"
}
```

### Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `error.security.api-key-invalid` | Invalid API key | Check API key |
| `error.public-api.exceeded-api-key-allowance` | Rate limit exceeded | Reduce request rate |
| `error.position.size-increment` | Invalid position size | Check min/max size |
| `error.positions.not-found` | Position not found | Verify deal ID |
| `error.invalid.daterange` | Invalid date range | Check date format |
| `error.confirms.deal-not-found` | Deal confirmation not found | Wait and retry |

## Rate Limiting

### Limits
- **REST API**: 60 requests per minute
- **Historical Data**: 10,000 data points per week
- **Streaming**: Unlimited for subscribed items

### Best Practices
```python
import time
from functools import wraps

def rate_limit(calls_per_second=1):
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

@rate_limit(calls_per_second=1)
def make_api_call():
    # API call here
    pass
```

## Data Types

### Direction
- `BUY`: Long position
- `SELL`: Short position

### Order Type
- `MARKET`: Market order
- `LIMIT`: Limit order
- `STOP`: Stop order
- `QUOTE`: Quote order

### Time in Force
- `EXECUTE_AND_ELIMINATE`: Partial fill allowed
- `FILL_OR_KILL`: Full fill or cancel

### Resolution (Historical Data)
- `SECOND`
- `MINUTE`
- `MINUTE_2`
- `MINUTE_3`
- `MINUTE_5`
- `MINUTE_10`
- `MINUTE_15`
- `MINUTE_30`
- `HOUR`
- `HOUR_2`
- `HOUR_3`
- `HOUR_4`
- `DAY`
- `WEEK`
- `MONTH`

### Market Status
- `TRADEABLE`: Market open
- `CLOSED`: Market closed
- `EDITS_ONLY`: Can only edit positions
- `OFFLINE`: Market offline
- `AUCTION`: In auction
- `AUCTION_NO_EDITS`: Auction, no edits

## Integration Best Practices

### Connection Management
```python
class IGConnection:
    def __init__(self):
        self.session = requests.Session()
        self.cst_token = None
        self.security_token = None
        
    def login(self):
        # Login logic with retry
        pass
        
    def keep_alive(self):
        # Periodic keep-alive
        pass
        
    def reconnect(self):
        # Auto-reconnection logic
        pass
```

### Error Recovery
```python
def api_call_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

### Data Validation
```python
def validate_position_request(request):
    assert request['size'] >= min_deal_size
    assert request['size'] <= max_deal_size
    assert request['stopDistance'] >= min_stop_distance
    # Additional validations
```

## Testing

### Demo Environment
- Use demo credentials and endpoints
- No real money involved
- Same API structure as live
- May have delayed data

### Test Scenarios
1. Authentication and session management
2. Market data retrieval
3. Position opening/closing
4. Stop loss and take profit
5. Working orders
6. Error handling
7. Streaming data
8. Rate limiting

## Migration to Production

### Checklist
- [ ] Change API endpoints from demo to live
- [ ] Update credentials to live account
- [ ] Test with minimal position sizes
- [ ] Verify error handling
- [ ] Enable production logging
- [ ] Set up monitoring alerts
- [ ] Configure rate limiting
- [ ] Test failover procedures