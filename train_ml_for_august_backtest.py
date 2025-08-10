#!/usr/bin/env python3
"""
Train ML Models for August 8th Backtest
Train only on data BEFORE August 8th to avoid data leakage
"""

import os
import sys
import joblib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from models.ml_predictor import MLTradingPredictor
from data.db import db, sanitize_collection_name
import pandas as pd
from datetime import datetime, timedelta

def train_ml_for_backtest():
    print("🤖 Training ML Models for August 8th Backtest")
    print("=" * 60)
    print("📅 Using ONLY pre-August 8th data (no future data leakage)")
    print("=" * 60)
    
    # August 8th cutoff - use only data BEFORE this date
    august_8_cutoff = datetime(2025, 8, 8, 0, 0, 0)
    
    markets = ["FTSE 100", "DAX"]
    trained_models = {}
    
    for market in markets:
        print(f"\n📈 Training ML models for {market}...")
        
        try:
            # Get market-specific collection
            collection_name = sanitize_collection_name(market)
            
            if collection_name not in db.list_collection_names():
                print(f"❌ No tick data found for {market}")
                continue
            
            tick_collection = db[collection_name]
            
            # Use ALL data before August 8th
            print(f"📊 Fetching all data before August 8th for {market}...")
            cursor = tick_collection.find({
                "timestamp": {"$lt": august_8_cutoff}
            }).sort("timestamp", 1)
            
            ticks = list(cursor)
            
            if len(ticks) < 1000:
                print(f"⚠️ Insufficient data for {market}: {len(ticks)} ticks")
                continue
            
            print(f"✅ Loaded {len(ticks)} pre-August 8th data points for {market}")
            
            # Convert to DataFrame
            df = pd.DataFrame(ticks)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)
            df["midprice"] = (df["bid"] + df["offer"]) / 2
            
            print(f"📊 {market} training data range: {df.index[0]} to {df.index[-1]}")
            print(f"   Price range: £{df['midprice'].min():.2f} - £{df['midprice'].max():.2f}")
            
            # Train Random Forest model
            print(f"🤖 Training Random Forest for {market}...")
            rf_model = MLTradingPredictor(model_type="random_forest")
            
            rf_results = rf_model.train(
                df=df,
                test_size=0.2,
                lookahead_periods=5,
                threshold=0.8  # Stricter threshold for August 8th
            )
            
            print(f"📊 {market} Random Forest Results:")
            print(f"   Train Accuracy: {rf_results['train_accuracy']:.3f}")
            print(f"   Test Accuracy: {rf_results['test_accuracy']:.3f}")
            
            # Train Gradient Boosting model  
            print(f"🚀 Training Gradient Boosting for {market}...")
            gb_model = MLTradingPredictor(model_type="gradient_boosting")
            
            gb_results = gb_model.train(
                df=df,
                test_size=0.2,
                lookahead_periods=5,
                threshold=0.8
            )
            
            print(f"📊 {market} Gradient Boosting Results:")
            print(f"   Train Accuracy: {gb_results['train_accuracy']:.3f}")
            print(f"   Test Accuracy: {gb_results['test_accuracy']:.3f}")
            
            # Save models for backtest
            rf_filename = f"models/ml_backtest_{market.replace(' ', '_').lower()}_rf.pkl"
            gb_filename = f"models/ml_backtest_{market.replace(' ', '_').lower()}_gb.pkl"
            
            rf_model.save_model(rf_filename)
            gb_model.save_model(gb_filename)
            
            # Test latest prediction before August 8th
            print(f"🔮 Testing prediction on pre-August 8th data...")
            test_data = df.tail(100)
            rf_pred = rf_model.predict(test_data)
            gb_pred = gb_model.predict(test_data)
            
            print(f"📈 {market} Pre-August 8th Predictions:")
            print(f"   RF: {rf_pred['signal']} (confidence: {rf_pred['confidence']:.3f})")
            print(f"   GB: {gb_pred['signal']} (confidence: {gb_pred['confidence']:.3f})")
            
            trained_models[market] = {
                'rf_model': rf_model,
                'gb_model': gb_model,
                'rf_filename': rf_filename,
                'gb_filename': gb_filename,
                'rf_results': rf_results,
                'gb_results': gb_results
            }
            
        except Exception as e:
            print(f"❌ Training failed for {market}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🎯 ML Training Summary:")
    print(f"   Markets trained: {len(trained_models)}")
    for market, models in trained_models.items():
        print(f"   {market}:")
        print(f"      RF Accuracy: {models['rf_results']['test_accuracy']:.3f}")
        print(f"      GB Accuracy: {models['gb_results']['test_accuracy']:.3f}")
    
    print(f"\n✅ ML models ready for August 8th backtest!")
    print(f"💾 Models saved for integration with backtest system")
    
    return trained_models

if __name__ == "__main__":
    train_ml_for_backtest()