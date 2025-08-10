# runners/train_ml_model.py

import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.ml_predictor import MLTradingPredictor
from data.db import db, sanitize_collection_name

def fetch_training_data(asset: str, days_back: int = 30) -> pd.DataFrame:
    """
    Fetch historical data for ML model training.
    
    Parameters:
    - asset: Asset name
    - days_back: Number of days of historical data
    
    Returns:
    - DataFrame with historical price data
    """
    
    print(f"📊 Fetching {days_back} days of data for {asset}...")
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    # Get market-specific collection
    collection_name = sanitize_collection_name(asset)
    
    # Check if collection exists
    if collection_name not in db.list_collection_names():
        raise ValueError(f"No tick data found for {asset}. Collection '{collection_name}' does not exist.")
    
    tick_collection = db[collection_name]
    
    # Query MongoDB
    cursor = tick_collection.find({
        "timestamp": {"$gte": start_date, "$lte": end_date}
    }).sort("timestamp", 1)
    
    ticks = list(cursor)
    
    if len(ticks) < 1000:
        raise ValueError(f"Insufficient data for training. Got {len(ticks)} ticks, need at least 1000.")
    
    # Convert to DataFrame
    df = pd.DataFrame(ticks)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    df["midprice"] = (df["bid"] + df["offer"]) / 2
    
    print(f"✅ Loaded {len(df)} data points from {df.index[0]} to {df.index[-1]}")
    
    return df

def main():
    """Main function to train ML models."""
    
    print("🤖 ML Model Training System")
    print("="*50)
    
    # Configuration
    print("\n⚙️ Training Configuration:")
    
    # Select asset
    print("\nAvailable assets for training:")
    print("1. FTSE 100 (Index)")
    print("2. META (US Stock)")
    print("3. GOOGL (US Stock)")
    print("4. AAPL (US Stock)")
    print("5. Custom asset")
    
    choice = input("\nSelect asset (1-5): ").strip()
    
    asset_map = {
        "1": "FTSE 100",
        "2": "META", 
        "3": "GOOGL",
        "4": "AAPL"
    }
    
    if choice in asset_map:
        asset = asset_map[choice]
    elif choice == "5":
        asset = input("Enter custom asset name: ").strip()
    else:
        print("❌ Invalid choice. Using FTSE 100.")
        asset = "FTSE 100"
    
    print(f"📈 Selected asset: {asset}")
    
    # Training parameters
    try:
        days_back = int(input("Days of historical data (default 30): ").strip() or "30")
        lookahead = int(input("Prediction lookahead periods (default 5): ").strip() or "5")
        threshold = float(input("Signal threshold % (default 1.0): ").strip() or "1.0")
    except ValueError:
        print("⚠️ Invalid input. Using defaults.")
        days_back = 30
        lookahead = 5
        threshold = 1.0
    
    # Model type selection
    print("\n🧠 Model Type:")
    print("1. Random Forest (default, good for beginners)")
    print("2. Gradient Boosting (more advanced)")
    
    model_choice = input("Select model type (1-2): ").strip()
    model_type = "gradient_boosting" if model_choice == "2" else "random_forest"
    
    print(f"\n🎯 Training Configuration:")
    print(f"  • Asset: {asset}")
    print(f"  • Historical Data: {days_back} days")
    print(f"  • Lookahead: {lookahead} periods")
    print(f"  • Threshold: {threshold}%")
    print(f"  • Model: {model_type}")
    
    confirm = input("\nProceed with training? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("❌ Training cancelled.")
        return
    
    try:
        # Fetch training data
        df = fetch_training_data(asset, days_back)
        
        # Initialize ML model
        print(f"\n🤖 Initializing {model_type} model...")
        ml_model = MLTradingPredictor(model_type=model_type)
        
        # Train the model
        print("\n🎓 Starting training process...")
        training_results = ml_model.train(
            df=df,
            test_size=0.2,
            lookahead_periods=lookahead,
            threshold=threshold
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
            print(f"  • Probabilities: BUY: {probs['BUY']:.3f}, SELL: {probs['SELL']:.3f}, HOLD: {probs['HOLD']:.3f}")
        
        # Save model
        save_model = input(f"\n💾 Save trained model? (Y/n): ").strip().lower()
        if save_model != 'n':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = f"ml_model_{asset.replace(' ', '_')}_{model_type}_{timestamp}.pkl"
            
            ml_model.save_model(model_filename)
            print(f"✅ Model saved as: {model_filename}")
            
            # Instructions for using the model
            print(f"\n📖 To use this model in your trading system:")
            print(f"  1. Copy {model_filename} to your models directory")
            print(f"  2. Load it using: ml_predictor.load_model('{model_filename}')")
            print(f"  3. The model will then be used in the advanced strategy engine")
    
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()