# models/ml_predictor.py

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import joblib
import warnings
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