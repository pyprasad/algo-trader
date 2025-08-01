# core/advanced_strategy_engine.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yaml
import sys
import os
from typing import Dict, List, Tuple, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.db import collection as mongo_collection
from core.ensemble_strategy import ensemble_strategy
from models.ml_predictor import ml_predictor
from core.asset_manager import asset_manager
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Load global configuration
try:
    with open("configs/global.yaml", "r") as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    config = {
        "strategy": {
            "rsi_period": 14,
            "mode": "HISTORICAL"
        }
    }

class AdvancedStrategyEngine:
    """
    Advanced multi-asset strategy engine that combines:
    - Ensemble of technical strategies
    - Machine learning predictions
    - Multi-asset portfolio management
    - Risk-adjusted position sizing
    """
    
    def __init__(self):
        self.ensemble = ensemble_strategy
        self.ml_model = ml_predictor
        self.asset_mgr = asset_manager
        
        # Strategy configuration
        self.use_ml_predictions = True
        self.ml_weight = 0.3  # Weight of ML predictions in final decision
        self.ensemble_weight = 0.7  # Weight of ensemble strategies
        
        # Risk management parameters
        self.max_portfolio_risk = 0.10  # Maximum 10% of portfolio at risk
        self.max_correlation_threshold = 0.7  # Maximum correlation between assets
        
    def get_market_data(self, asset: str, lookback_minutes: int = 60) -> Optional[pd.DataFrame]:
        """
        Fetch market data for a specific asset.
        
        Parameters:
        - asset: Asset name
        - lookback_minutes: Minutes of historical data to fetch
        
        Returns:
        - DataFrame with market data or None if insufficient data
        """
        
        since = datetime.utcnow() - timedelta(minutes=lookback_minutes)
        
        # Query MongoDB for asset data
        cursor = mongo_collection.find(
            {"market": asset, "timestamp": {"$gte": since}}
        ).sort("timestamp", 1)
        
        ticks = list(cursor)
        
        if len(ticks) < 50:  # Need minimum data for analysis
            print(f"❌ Insufficient data for {asset}: {len(ticks)} ticks")
            return None
        
        df = pd.DataFrame(ticks)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        df["midprice"] = (df["bid"] + df["offer"]) / 2
        
        return df
    
    def analyze_single_asset(self, asset: str, lookback_minutes: int = 60) -> Dict:
        """
        Perform comprehensive analysis on a single asset.
        
        Parameters:
        - asset: Asset name
        - lookback_minutes: Historical data period
        
        Returns:
        - Dictionary with analysis results
        """
        
        # Get market data
        df = self.get_market_data(asset, lookback_minutes)
        if df is None:
            return {
                "asset": asset,
                "signal": "HOLD",
                "confidence": 0.0,
                "error": "Insufficient data"
            }
        
        # Check if asset is tradeable now
        is_tradeable = self.asset_mgr.is_asset_tradeable_now(asset)
        
        analysis_results = {
            "asset": asset,
            "is_tradeable": is_tradeable,
            "data_points": len(df),
            "price_latest": float(df["midprice"].iloc[-1]),
            "timestamp": df.index[-1].isoformat()
        }
        
        try:
            # 1. Ensemble strategy analysis
            ensemble_signal, ensemble_details = self.ensemble.generate_ensemble_signal(df)
            analysis_results["ensemble"] = {
                "signal": ensemble_signal,
                "confidence": ensemble_details["total_confidence"],
                "details": ensemble_details
            }
            
            # 2. Machine learning prediction (if model is trained)
            ml_results = {"signal": "HOLD", "confidence": 0.0}
            if self.use_ml_predictions and self.ml_model.is_trained:
                ml_results = self.ml_model.predict(df)
            
            analysis_results["ml_prediction"] = ml_results
            
            # 3. Combine ensemble and ML signals
            final_signal, final_confidence = self._combine_signals(
                ensemble_signal, ensemble_details["total_confidence"],
                ml_results["signal"], ml_results["confidence"]
            )
            
            analysis_results["final_signal"] = final_signal
            analysis_results["final_confidence"] = final_confidence
            
            # 4. Position sizing recommendation
            if final_signal in ["BUY", "SELL"]:
                position_size = self.asset_mgr.get_position_size(asset, 10000)  # Assume $10k account
                stop_loss = self.asset_mgr.get_stop_loss_distance(asset)
                take_profit = self.asset_mgr.get_take_profit_distance(asset, stop_loss)
                
                analysis_results["position_sizing"] = {
                    "recommended_size": position_size,
                    "stop_loss_distance": stop_loss,
                    "take_profit_distance": take_profit
                }
            
        except Exception as e:
            analysis_results["error"] = str(e)
            analysis_results["final_signal"] = "HOLD"
            analysis_results["final_confidence"] = 0.0
        
        return analysis_results
    
    def _combine_signals(self, ensemble_signal: str, ensemble_confidence: float,
                        ml_signal: str, ml_confidence: float) -> Tuple[str, float]:
        """
        Combine ensemble and ML signals with weighted voting.
        
        Returns:
        - Tuple of (final_signal, final_confidence)
        """
        
        # Convert signals to numeric scores
        signal_scores = {"BUY": 1, "HOLD": 0, "SELL": -1}
        
        ensemble_score = signal_scores[ensemble_signal] * ensemble_confidence * self.ensemble_weight
        ml_score = signal_scores[ml_signal] * ml_confidence * self.ml_weight
        
        combined_score = ensemble_score + ml_score
        combined_confidence = (ensemble_confidence * self.ensemble_weight + 
                             ml_confidence * self.ml_weight)
        
        # Determine final signal
        if combined_score > 0.2:
            final_signal = "BUY"
        elif combined_score < -0.2:
            final_signal = "SELL"
        else:
            final_signal = "HOLD"
        
        # Apply minimum confidence threshold
        if combined_confidence < 0.4:
            final_signal = "HOLD"
            combined_confidence = 0.0
        
        return final_signal, combined_confidence
    
    def analyze_portfolio(self, assets: List[str], lookback_minutes: int = 60) -> Dict:
        """
        Analyze multiple assets and provide portfolio-level recommendations.
        
        Parameters:
        - assets: List of asset names to analyze
        - lookback_minutes: Historical data period
        
        Returns:
        - Dictionary with portfolio analysis
        """
        
        print(f"🔍 Analyzing portfolio of {len(assets)} assets...")
        
        portfolio_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "assets_analyzed": len(assets),
            "tradeable_assets": 0,
            "buy_signals": 0,
            "sell_signals": 0,
            "hold_signals": 0,
            "asset_analyses": {},
            "portfolio_recommendations": []
        }
        
        asset_analyses = []
        
        # Analyze each asset
        for asset in assets:
            print(f"  📊 Analyzing {asset}...")
            analysis = self.analyze_single_asset(asset, lookback_minutes)
            portfolio_results["asset_analyses"][asset] = analysis
            
            if analysis.get("is_tradeable", False):
                portfolio_results["tradeable_assets"] += 1
                
                signal = analysis.get("final_signal", "HOLD")
                if signal == "BUY":
                    portfolio_results["buy_signals"] += 1
                elif signal == "SELL":
                    portfolio_results["sell_signals"] += 1
                else:
                    portfolio_results["hold_signals"] += 1
                
                # Collect for portfolio optimization
                if signal in ["BUY", "SELL"] and analysis.get("final_confidence", 0) > 0.5:
                    asset_analyses.append(analysis)
        
        # Portfolio-level recommendations
        if asset_analyses:
            portfolio_results["portfolio_recommendations"] = self._generate_portfolio_recommendations(asset_analyses)
        
        return portfolio_results
    
    def _generate_portfolio_recommendations(self, asset_analyses: List[Dict]) -> List[Dict]:
        """
        Generate portfolio-level trading recommendations considering correlations and risk.
        
        Parameters:
        - asset_analyses: List of asset analysis results
        
        Returns:
        - List of recommended trades
        """
        
        recommendations = []
        
        # Sort by confidence (highest first)
        asset_analyses.sort(key=lambda x: x.get("final_confidence", 0), reverse=True)
        
        total_risk_allocated = 0.0
        max_positions = 5  # Maximum number of positions
        
        for analysis in asset_analyses[:max_positions]:
            asset = analysis["asset"]
            signal = analysis["final_signal"]
            confidence = analysis["final_confidence"]
            
            # Calculate risk allocation
            risk_per_trade = min(0.02 * confidence, 0.05)  # Max 5% per trade
            
            if total_risk_allocated + risk_per_trade <= self.max_portfolio_risk:
                position_sizing = analysis.get("position_sizing", {})
                
                recommendation = {
                    "asset": asset,
                    "signal": signal,
                    "confidence": confidence,
                    "risk_allocation": risk_per_trade,
                    "priority": len(recommendations) + 1,
                    "position_size": position_sizing.get("recommended_size", 1),
                    "stop_loss": position_sizing.get("stop_loss_distance", 10),
                    "take_profit": position_sizing.get("take_profit_distance", 20)
                }
                
                recommendations.append(recommendation)
                total_risk_allocated += risk_per_trade
            else:
                # Portfolio risk limit reached
                break
        
        return recommendations
    
    def run_advanced_strategy(self, assets: Optional[List[str]] = None, 
                            lookback_minutes: int = 60) -> Dict:
        """
        Run the complete advanced strategy analysis.
        
        Parameters:
        - assets: List of assets to analyze (if None, uses tradeable assets)
        - lookback_minutes: Historical data period
        
        Returns:
        - Complete strategy results
        """
        
        if assets is None:
            # Get all tradeable assets
            all_assets = self.asset_mgr.get_tradeable_assets()
            # Filter to currently tradeable assets
            assets = [asset for asset in all_assets if self.asset_mgr.is_asset_tradeable_now(asset)]
            
            if not assets:
                assets = ["FTSE 100"]  # Fallback to default
        
        print(f"🚀 Running Advanced Strategy Engine...")
        print(f"📈 Target Assets: {', '.join(assets)}")
        print(f"⏱️  Lookback Period: {lookback_minutes} minutes")
        print("="*60)
        
        # Perform portfolio analysis
        results = self.analyze_portfolio(assets, lookback_minutes)
        
        # Add summary statistics
        results["summary"] = {
            "total_assets": len(assets),
            "tradeable_now": results["tradeable_assets"],
            "strong_signals": len([a for a in results["asset_analyses"].values() 
                                 if a.get("final_confidence", 0) > 0.6]),
            "recommended_trades": len(results["portfolio_recommendations"]),
            "portfolio_risk": sum([r["risk_allocation"] for r in results["portfolio_recommendations"]])
        }
        
        return results

# Global advanced strategy instance
advanced_strategy = AdvancedStrategyEngine()