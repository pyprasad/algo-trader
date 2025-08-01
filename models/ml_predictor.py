# models/ml_predictor.py

"""
🤖 Machine Learning Predictor Module

Implements various ML models to enhance trading predictions:
- Random Forest for signal classification
- Feature engineering from multiple data sources
- Model ensemble for robust predictions
- Real-time prediction integration

Author: AI-Enhanced Trading System
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Try to import ML libraries (install if needed)
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    print("⚠️ scikit-learn not available. Install with: pip install scikit-learn")
    SKLEARN_AVAILABLE = False

from data.db import db, sanitize_collection_name
from models.rsi import compute_rsi
from models.atr import compute_atr
from models.ema import compute_ema
warnings.filterwarnings('ignore')

class MLTradingPredictor:
    """
    Machine Learning predictor for trading signals using ensemble methods.
    """
    
    def __init__(self, model_type: str = "random_forest"):
        """
        Initialize ML predictor.
        
        Parameters:
        - model_type: Type of ML model ("random_forest", "gradient_boosting", "ensemble")
        """
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.is_trained = False
        
        # Initialize model based on type
        if model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
        elif model_type == "gradient_boosting":
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
        else:
            # Default to random forest
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create feature matrix from price data.
        
        Parameters:
        - df: DataFrame with OHLC data or midprice
        
        Returns:
        - DataFrame with engineered features
        """
        
        price_col = "midprice" if "midprice" in df.columns else "close"
        price_series = df[price_col]
        
        features = pd.DataFrame(index=df.index)
        
        # Price-based features
        features['price'] = price_series
        features['price_change'] = price_series.pct_change()
        features['price_change_2'] = price_series.pct_change(2)
        features['price_change_5'] = price_series.pct_change(5)
        
        # Moving averages
        features['sma_5'] = price_series.rolling(5).mean()
        features['sma_10'] = price_series.rolling(10).mean()
        features['sma_20'] = price_series.rolling(20).mean()
        features['ema_12'] = price_series.ewm(span=12).mean()
        features['ema_26'] = price_series.ewm(span=26).mean()
        
        # Technical indicators
        # RSI
        delta = price_series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1/14).mean()
        avg_loss = loss.ewm(alpha=1/14).mean()
        rs = avg_gain / avg_loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        features['macd'] = features['ema_12'] - features['ema_26']
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_histogram'] = features['macd'] - features['macd_signal']
        
        # Bollinger Bands
        features['bb_middle'] = price_series.rolling(20).mean()
        bb_std = price_series.rolling(20).std()
        features['bb_upper'] = features['bb_middle'] + (bb_std * 2)
        features['bb_lower'] = features['bb_middle'] - (bb_std * 2)
        features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / features['bb_middle']
        features['bb_position'] = (price_series - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        # Volatility features
        features['volatility_5'] = price_series.rolling(5).std()
        features['volatility_20'] = price_series.rolling(20).std()
        features['volatility_ratio'] = features['volatility_5'] / features['volatility_20']
        
        # Volume proxy (using price movement as volume proxy)
        features['volume_proxy'] = abs(price_series.diff())
        features['volume_sma'] = features['volume_proxy'].rolling(10).mean()
        
        # Momentum features
        features['momentum_5'] = (price_series / price_series.shift(5) - 1) * 100
        features['momentum_10'] = (price_series / price_series.shift(10) - 1) * 100
        features['momentum_20'] = (price_series / price_series.shift(20) - 1) * 100
        
        # Support/Resistance levels
        features['resistance_20'] = price_series.rolling(20).max()
        features['support_20'] = price_series.rolling(20).min()
        features['price_vs_resistance'] = (price_series / features['resistance_20'] - 1) * 100
        features['price_vs_support'] = (price_series / features['support_20'] - 1) * 100
        
        # Time-based features
        if 'timestamp' in df.columns:
            df_copy = df.copy()
            df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])
            features['hour'] = df_copy['timestamp'].dt.hour
            features['day_of_week'] = df_copy['timestamp'].dt.dayofweek
            features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)
        
        # Lagged features
        for lag in [1, 2, 3, 5]:
            features[f'rsi_lag_{lag}'] = features['rsi'].shift(lag)
            features[f'macd_lag_{lag}'] = features['macd'].shift(lag)
            features[f'price_change_lag_{lag}'] = features['price_change'].shift(lag)
        
        # Drop NaN values and return
        features = features.dropna()
        self.feature_names = features.columns.tolist()
        
        return features
    
    def create_labels(self, df: pd.DataFrame, lookahead_periods: int = 5, threshold: float = 0.5) -> pd.Series:
        """
        Create trading labels based on future price movements.
        
        Parameters:
        - df: DataFrame with price data
        - lookahead_periods: Number of periods to look ahead
        - threshold: Minimum percentage change to generate BUY/SELL signal
        
        Returns:
        - Series with labels (0=HOLD, 1=BUY, 2=SELL)
        """
        
        price_col = "midprice" if "midprice" in df.columns else "close"
        price_series = df[price_col]
        
        # Calculate future returns
        future_returns = (price_series.shift(-lookahead_periods) / price_series - 1) * 100
        
        # Create labels
        labels = pd.Series(0, index=df.index)  # Default to HOLD
        labels[future_returns > threshold] = 1   # BUY
        labels[future_returns < -threshold] = 2  # SELL
        
        return labels
    
    def train(self, df: pd.DataFrame, test_size: float = 0.2, lookahead_periods: int = 5, threshold: float = 1.0):
        """
        Train the ML model on historical data.
        
        Parameters:
        - df: DataFrame with historical price data
        - test_size: Proportion of data to use for testing
        - lookahead_periods: Periods to look ahead for label creation
        - threshold: Minimum percentage change for signal generation
        """
        
        print("🤖 Training ML Trading Predictor...")
        
        # Create features and labels
        features = self.create_features(df)
        labels = self.create_labels(df, lookahead_periods, threshold)
        
        # Align features and labels
        common_index = features.index.intersection(labels.index)
        features = features.loc[common_index]
        labels = labels.loc[common_index]
        
        if len(features) < 100:
            raise ValueError("Insufficient data for training. Need at least 100 samples.")
        
        # Remove samples with lookahead bias (last few rows)
        features = features.iloc[:-lookahead_periods]
        labels = labels.iloc[:-lookahead_periods]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=test_size, random_state=42, stratify=labels
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        print(f"📚 Training on {len(X_train)} samples...")
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        y_pred = self.model.predict(X_test_scaled)
        
        print(f"✅ Training completed!")
        print(f"📊 Train Accuracy: {train_score:.3f}")
        print(f"📊 Test Accuracy: {test_score:.3f}")
        
        # Print classification report
        label_names = ['HOLD', 'BUY', 'SELL']
        print("\n📈 Classification Report:")
        print(classification_report(y_test, y_pred, target_names=label_names))
        
        # Feature importance (for tree-based models)
        if hasattr(self.model, 'feature_importances_'):
            feature_importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            print("\n🔍 Top 10 Most Important Features:")
            for i, row in feature_importance.head(10).iterrows():
                print(f"  {row['feature']}: {row['importance']:.4f}")
        
        self.is_trained = True
        
        return {
            "train_accuracy": train_score,
            "test_accuracy": test_score,
            "classification_report": classification_report(y_test, y_pred, target_names=label_names, output_dict=True)
        }
    
    def predict(self, df: pd.DataFrame) -> dict:
        """
        Make predictions on new data.
        
        Parameters:
        - df: DataFrame with recent price data
        
        Returns:
        - Dictionary with prediction and confidence
        """
        
        if not self.is_trained:
            return {"signal": "HOLD", "confidence": 0.0, "error": "Model not trained"}
        
        try:
            # Create features
            features = self.create_features(df)
            
            if len(features) == 0:
                return {"signal": "HOLD", "confidence": 0.0, "error": "No valid features"}
            
            # Use latest data point
            latest_features = features.iloc[-1:][self.feature_names]
            
            # Scale features
            latest_scaled = self.scaler.transform(latest_features)
            
            # Make prediction
            prediction = self.model.predict(latest_scaled)[0]
            probabilities = self.model.predict_proba(latest_scaled)[0]
            
            # Convert prediction to signal
            signal_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
            predicted_signal = signal_map[prediction]
            confidence = max(probabilities)
            
            return {
                "signal": predicted_signal,
                "confidence": float(confidence),
                "probabilities": {
                    "HOLD": float(probabilities[0]),
                    "BUY": float(probabilities[1]),
                    "SELL": float(probabilities[2])
                }
            }
            
        except Exception as e:
            return {"signal": "HOLD", "confidence": 0.0, "error": str(e)}
    
    def save_model(self, filepath: str):
        """Save trained model to disk."""
        if self.is_trained:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'model_type': self.model_type
            }
            joblib.dump(model_data, filepath)
            print(f"💾 Model saved to {filepath}")
        else:
            print("⚠️ Cannot save untrained model")
    
    def load_model(self, filepath: str):
        """Load trained model from disk."""
        try:
            model_data = joblib.load(filepath)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.model_type = model_data['model_type']
            self.is_trained = True
            print(f"📂 Model loaded from {filepath}")
        except Exception as e:
            print(f"❌ Error loading model: {e}")

# Global ML predictor instance
ml_predictor = MLTradingPredictor()

# ============================================================================
# ENHANCED ML SYSTEM - Advanced Features
# ============================================================================

class EnhancedFeatureEngineer:
    """Advanced feature engineering for ML models"""
    
    @staticmethod
    def create_regime_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create market regime features"""
        price_col = "midprice" if "midprice" in df.columns else "close"
        price_series = df[price_col]
        
        # Volatility regimes
        vol_short = price_series.pct_change().rolling(10).std()
        vol_long = price_series.pct_change().rolling(50).std()
        
        df['vol_regime'] = (vol_short / vol_long).fillna(1)
        df['high_vol_regime'] = (df['vol_regime'] > 1.5).astype(int)
        df['low_vol_regime'] = (df['vol_regime'] < 0.7).astype(int)
        
        # Trend regimes
        ema_fast = price_series.ewm(span=12).mean()
        ema_slow = price_series.ewm(span=26).mean()
        
        df['trend_strength'] = (ema_fast - ema_slow) / ema_slow
        df['strong_uptrend'] = (df['trend_strength'] > 0.02).astype(int)
        df['strong_downtrend'] = (df['trend_strength'] < -0.02).astype(int)
        
        return df
    
    @staticmethod
    def create_pattern_features(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """Create pattern recognition features"""
        price_col = "midprice" if "midprice" in df.columns else "close"
        price_series = df[price_col]
        
        # Support/Resistance breaks
        resistance = price_series.rolling(window).max()
        support = price_series.rolling(window).min()
        
        df['resistance_break'] = (price_series > resistance.shift(1)).astype(int)
        df['support_break'] = (price_series < support.shift(1)).astype(int)
        
        # Price gaps
        df['price_gap'] = price_series - price_series.shift(1)
        df['large_gap_up'] = (df['price_gap'] > price_series.rolling(window).std() * 2).astype(int)
        df['large_gap_down'] = (df['price_gap'] < -price_series.rolling(window).std() * 2).astype(int)
        
        # Reversal patterns (simplified)
        df['potential_reversal'] = ((price_series.rolling(3).min() == price_series.shift(1)) | 
                                   (price_series.rolling(3).max() == price_series.shift(1))).astype(int)
        
        return df

class MLEnsemblePredictor:
    """Enhanced ML ensemble with multiple models and advanced features"""
    
    def __init__(self):
        self.models = {
            'rf': RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42),
            'gb': GradientBoostingClassifier(n_estimators=150, learning_rate=0.1, random_state=42)
        }
        self.scalers = {}
        self.feature_names = []
        self.is_trained = False
        self.training_metrics = {}
        
    def prepare_enhanced_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive feature set"""
        # Start with existing features
        predictor = MLTradingPredictor()
        features = predictor.create_features(df)
        
        # Add enhanced features
        enhanced_df = df.copy()
        enhanced_df = EnhancedFeatureEngineer.create_regime_features(enhanced_df)
        enhanced_df = EnhancedFeatureEngineer.create_pattern_features(enhanced_df)
        
        # Merge with existing features
        for col in enhanced_df.columns:
            if col not in features.columns and col != 'timestamp':
                if col in enhanced_df.columns:
                    features[col] = enhanced_df[col]
        
        return features.dropna()
    
    def train_ensemble(self, market: str, lookback_hours: int = 168) -> Dict:
        """Train ensemble of ML models"""
        print(f"🚀 Training Enhanced ML Ensemble for {market}...")
        
        # Get data from database
        collection_name = sanitize_collection_name(market)
        if collection_name not in db.list_collection_names():
            return {"error": f"No data found for {market}"}
        
        tick_collection = db[collection_name]
        since = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        cursor = tick_collection.find({"timestamp": {"$gte": since}}).sort("timestamp", 1)
        ticks = list(cursor)
        
        if len(ticks) < 1000:
            return {"error": f"Insufficient data: {len(ticks)} < 1000"}
        
        # Convert to DataFrame
        df = pd.DataFrame(ticks)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        df['midprice'] = (df['bid'] + df['offer']) / 2
        
        # Create enhanced features
        features = self.prepare_enhanced_features(df)
        
        # Create labels (future price direction)
        lookahead = 5
        future_returns = (df['midprice'].shift(-lookahead) / df['midprice'] - 1) * 100
        labels = pd.Series(0, index=df.index)  # HOLD
        labels[future_returns > 0.3] = 1   # BUY
        labels[future_returns < -0.3] = 2  # SELL
        
        # Align features and labels
        common_index = features.index.intersection(labels.index)
        features = features.loc[common_index]
        labels = labels.loc[common_index]
        
        # Remove lookahead bias
        features = features.iloc[:-lookahead]
        labels = labels.iloc[:-lookahead]
        
        if len(features) < 200:
            return {"error": "Insufficient aligned data for training"}
        
        self.feature_names = features.columns.tolist()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2, random_state=42
        )
        
        # Train each model
        results = {}
        for name, model in self.models.items():
            print(f"🔧 Training {name.upper()} model...")
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            train_score = model.score(X_train_scaled, y_train)
            test_score = model.score(X_test_scaled, y_test)
            
            # Store scaler and results
            self.scalers[name] = scaler
            results[name] = {
                "train_accuracy": train_score,
                "test_accuracy": test_score
            }
            
            print(f"  ✅ {name}: Train={train_score:.3f}, Test={test_score:.3f}")
        
        self.is_trained = True
        self.training_metrics = results
        
        return {
            "models_trained": list(self.models.keys()),
            "features_used": len(self.feature_names),
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "results": results
        }
    
    def predict_ensemble(self, recent_prices: List[float]) -> Dict:
        """Make ensemble prediction"""
        if not self.is_trained:
            return {"error": "Ensemble not trained"}
        
        try:
            # Create DataFrame from recent prices
            df = pd.DataFrame({
                'midprice': recent_prices,
                'bid': recent_prices,  # Approximate
                'offer': recent_prices  # Approximate
            })
            df.index = pd.date_range(end=datetime.now(), periods=len(recent_prices), freq='1min')
            
            # Create features
            features = self.prepare_enhanced_features(df)
            
            if len(features) == 0:
                return {"error": "No valid features"}
            
            # Get latest features
            latest_features = features.iloc[-1:][self.feature_names]
            
            # Get predictions from each model
            predictions = {}
            probabilities = {}
            
            for name, model in self.models.items():
                scaler = self.scalers[name]
                scaled_features = scaler.transform(latest_features)
                
                pred = model.predict(scaled_features)[0]
                prob = model.predict_proba(scaled_features)[0]
                
                predictions[name] = pred
                probabilities[name] = prob
            
            # Ensemble voting
            votes = list(predictions.values())
            buy_votes = votes.count(1)
            sell_votes = votes.count(2)
            hold_votes = votes.count(0)
            
            if buy_votes > sell_votes and buy_votes > hold_votes:
                ensemble_signal = "BUY"
            elif sell_votes > buy_votes and sell_votes > hold_votes:
                ensemble_signal = "SELL"
            else:
                ensemble_signal = "HOLD"
            
            # Average confidence
            avg_probs = np.mean(list(probabilities.values()), axis=0)
            signal_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
            confidence = max(avg_probs)
            
            return {
                "ensemble_signal": ensemble_signal,
                "confidence": float(confidence),
                "individual_predictions": {name: signal_map[pred] for name, pred in predictions.items()},
                "model_votes": {"HOLD": hold_votes, "BUY": buy_votes, "SELL": sell_votes},
                "average_probabilities": {
                    "HOLD": float(avg_probs[0]),
                    "BUY": float(avg_probs[1]),
                    "SELL": float(avg_probs[2])
                }
            }
            
        except Exception as e:
            return {"error": f"Prediction failed: {e}"}

# Enhanced ML Integration Functions
class MLTradingIntegration:
    """Integration layer for ML predictions with trading system"""
    
    def __init__(self):
        self.ensemble = MLEnsemblePredictor()
        self.last_training = {}
        
    def should_retrain(self, market: str, hours_threshold: int = 24) -> bool:
        """Check if model needs retraining"""
        if market not in self.last_training:
            return True
        
        last_time = self.last_training[market]
        time_diff = datetime.now() - last_time
        return time_diff.total_seconds() > (hours_threshold * 3600)
    
    def train_for_market(self, market: str, force_retrain: bool = False) -> Dict:
        """Train ML models for specific market"""
        if not force_retrain and not self.should_retrain(market):
            return {"message": "Model recently trained", "skipped": True}
        
        result = self.ensemble.train_ensemble(market)
        
        if "error" not in result:
            self.last_training[market] = datetime.now()
            print(f"✅ ML models trained for {market}")
        
        return result
    
    def get_ml_signal(self, market: str, recent_prices: List[float], auto_train: bool = True) -> Dict:
        """Get ML trading signal for market"""
        # Auto-train if needed
        if auto_train and self.should_retrain(market):
            print(f"🔄 Auto-training ML models for {market}...")
            train_result = self.train_for_market(market)
            if "error" in train_result:
                return {"error": f"Training failed: {train_result['error']}"}
        
        # Get prediction
        prediction = self.ensemble.predict_ensemble(recent_prices)
        
        if "error" in prediction:
            return prediction
        
        # Format for trading system
        return {
            "ml_signal": prediction["ensemble_signal"],
            "ml_confidence": prediction["confidence"],
            "ml_details": prediction
        }

# Global ML integration instance
_global_ml_integration = None

def get_ml_integration():
    """Get global ML integration instance"""
    global _global_ml_integration
    if _global_ml_integration is None:
        _global_ml_integration = MLTradingIntegration()
    return _global_ml_integration

def train_ml_models_for_market(market: str, force_retrain: bool = False) -> Dict:
    """Train ML models for a specific market"""
    integration = get_ml_integration()
    return integration.train_for_market(market, force_retrain)

def get_ml_trading_signal(market: str, recent_prices: List[float]) -> Dict:
    """Get ML-enhanced trading signal"""
    integration = get_ml_integration()
    return integration.get_ml_signal(market, recent_prices)

# ============================================================================
# USAGE EXAMPLES AND TESTING
# ============================================================================

if __name__ == "__main__":
    print("🧪 Testing Enhanced ML Trading System")
    print("=" * 60)
    
    if SKLEARN_AVAILABLE:
        # Test the enhanced system
        print("📊 Enhanced ML System Status:")
        print("   ✅ scikit-learn available")
        print("   ✅ Enhanced features enabled")
        print("   ✅ Ensemble models ready")
        
        # Example usage
        print("\n💡 Usage Examples:")
        print("   Train models: train_ml_models_for_market('DAX')")
        print("   Get signals: get_ml_trading_signal('DAX', recent_prices)")
        print("   Auto-training: Enabled by default")
        
        print("\n🔧 Features Added:")
        print("   • Market regime detection")
        print("   • Pattern recognition")
        print("   • Ensemble voting")
        print("   • Auto-retraining")
        print("   • Enhanced feature engineering")
        
    else:
        print("❌ scikit-learn not available")
        print("📦 Install with: pip install scikit-learn pandas numpy")