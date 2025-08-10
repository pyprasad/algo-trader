#!/usr/bin/env python3
"""
Test ML training with FTSE 100 data
"""

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from models.ml_predictor import MLTradingPredictor
from data.db import db, sanitize_collection_name
import pandas as pd
from datetime import datetime, timedelta

def test_ml_training():
    print("🤖 Testing ML Training System")
    print("=" * 50)
    
    # Configuration
    asset = "FTSE 100"
    days_back = 7  # Use 7 days for quick test
    
    try:
        # Get market-specific collection
        collection_name = sanitize_collection_name(asset)
        
        # Check if collection exists
        if collection_name not in db.list_collection_names():
            print(f"❌ No tick data found for {asset}")
            return
        
        tick_collection = db[collection_name]
        
        # Calculate date range - use all available data for testing
        # Get the actual date range of data
        sample = tick_collection.find().sort("timestamp", -1).limit(1)
        latest_tick = list(sample)[0] if sample else None
        
        if latest_tick:
            end_date = latest_tick['timestamp'] + timedelta(hours=1)  # Add buffer
            start_date = end_date - timedelta(days=days_back)
        else:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
        
        print(f"📊 Fetching {days_back} days of data for {asset}...")
        print(f"   Collection: {collection_name}")
        print(f"   Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Query MongoDB
        cursor = tick_collection.find({
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }).sort("timestamp", 1)
        
        ticks = list(cursor)
        
        print(f"✅ Loaded {len(ticks)} data points")
        
        if len(ticks) < 1000:
            print(f"⚠️ Insufficient data for training. Got {len(ticks)} ticks, need at least 1000.")
            print("   Try increasing days_back parameter or collect more data")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(ticks)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        df["midprice"] = (df["bid"] + df["offer"]) / 2
        
        print(f"📈 Data range: {df.index[0]} to {df.index[-1]}")
        print(f"   Price range: £{df['midprice'].min():.2f} - £{df['midprice'].max():.2f}")
        
        # Initialize ML model
        print(f"\n🤖 Initializing Random Forest model...")
        ml_model = MLTradingPredictor(model_type="random_forest")
        
        # Train the model
        print("\n🎓 Starting training process...")
        training_results = ml_model.train(
            df=df,
            test_size=0.2,
            lookahead_periods=5,
            threshold=0.5  # Lower threshold for testing
        )
        
        # Show training results
        print(f"\n📊 Training Results:")
        print(f"  • Train Accuracy: {training_results['train_accuracy']:.3f}")
        print(f"  • Test Accuracy: {training_results['test_accuracy']:.3f}")
        
        # Test prediction on latest data
        print(f"\n🔮 Testing prediction on latest data...")
        recent_data = df.tail(100)  # Use last 100 points for prediction
        prediction = ml_model.predict(recent_data)
        
        print(f"📈 Latest Prediction:")
        print(f"  • Signal: {prediction['signal']}")
        print(f"  • Confidence: {prediction['confidence']:.3f}")
        
        if 'probabilities' in prediction:
            probs = prediction['probabilities']
            print(f"  • Probabilities:")
            print(f"    - BUY: {probs['BUY']:.3f}")
            print(f"    - SELL: {probs['SELL']:.3f}")
            print(f"    - HOLD: {probs['HOLD']:.3f}")
        
        print("\n✅ ML training test completed successfully!")
        
        if training_results['test_accuracy'] > 0.4:  # Better than random (33%)
            print("🎯 Model shows promising performance!")
        else:
            print("⚠️ Model performance is close to random - may need more data or feature tuning")
        
    except Exception as e:
        print(f"❌ Training test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ml_training()