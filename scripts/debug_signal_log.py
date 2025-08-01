# debug_signal_log.py

from pymongo import MongoClient
import pandas as pd

client = MongoClient("mongodb://127.0.0.1:27017/")
db = client["ftse100_scalping_bot"]
collection = db["ftse100"]

cursor = collection.find().sort("timestamp", -1).limit(100)
data = list(cursor)[::-1]
df = pd.DataFrame(data)
df["midprice"] = (df["bid"] + df["offer"]) / 2
df["ema"] = df["midprice"].ewm(span=50, adjust=False).mean()

delta = df["midprice"].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.rolling(window=14).mean()
avg_loss = loss.rolling(window=14).mean()
rs = avg_gain / avg_loss
df["rsi"] = 100 - (100 / (1 + rs))

df["high"] = df["midprice"]
df["low"] = df["midprice"]
df["close"] = df["midprice"]
df["prev_close"] = df["close"].shift(1)
df["tr"] = df[["high", "prev_close"]].max(axis=1) - df[["low", "prev_close"]].min(axis=1)
df["atr"] = df["tr"].rolling(window=14).mean()

print(df[["timestamp", "midprice", "ema", "rsi", "atr"]].tail(10))
