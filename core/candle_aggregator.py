# core/candle_aggregator.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yaml

class CandleAggregator:
    """
    Convert tick data to OHLC candles for different timeframes
    Configurable timeframes for better maintenance
    """
    
    def __init__(self, config_path='configs/timeframe_config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def ticks_to_candles(self, tick_df, timeframe='5T'):
        """
        Convert tick data to OHLC candles
        
        Args:
            tick_df: DataFrame with columns ['timestamp', 'bid', 'offer', 'midprice']
            timeframe: pandas frequency string ('1T', '5T', '15T', '1H', etc.)
            
        Returns:
            DataFrame with OHLC candles
        """
        if len(tick_df) == 0:
            return pd.DataFrame()
        
        # Ensure we have midprice
        if 'midprice' not in tick_df.columns:
            tick_df['midprice'] = (tick_df['bid'] + tick_df['offer']) / 2
        
        # Set timestamp as index for resampling
        df = tick_df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # Resample to create candles
        candles = df.resample(timeframe).agg({
            'midprice': ['first', 'max', 'min', 'last', 'count'],
            'bid': ['first', 'last'],
            'offer': ['first', 'last'],
        }).dropna()
        
        # Flatten column names
        candles.columns = ['open', 'high', 'low', 'close', 'volume', 'bid_open', 'bid_close', 'offer_open', 'offer_close']
        
        # Calculate spread and other metrics
        candles['spread'] = candles['offer_close'] - candles['bid_close']
        candles['typical_price'] = (candles['high'] + candles['low'] + candles['close']) / 3
        
        # Add candle patterns
        candles['body_size'] = abs(candles['close'] - candles['open'])
        candles['upper_wick'] = candles['high'] - np.maximum(candles['open'], candles['close'])
        candles['lower_wick'] = np.minimum(candles['open'], candles['close']) - candles['low']
        candles['is_bullish'] = candles['close'] > candles['open']
        
        # Reset index to have timestamp as column
        candles.reset_index(inplace=True)
        
        return candles
    
    def filter_by_session(self, candles_df, session_name):
        """
        Filter candles by trading session
        
        Args:
            candles_df: DataFrame with timestamp column
            session_name: 'london', 'new_york', 'overlap', etc.
            
        Returns:
            Filtered DataFrame
        """
        if session_name not in self.config['sessions']:
            return candles_df
        
        session = self.config['sessions'][session_name]
        if not session['enabled']:
            return candles_df
        
        # Convert times to datetime for filtering
        start_time = session['start_time']
        end_time = session['end_time']
        
        # Filter by time of day
        candles_df['hour'] = candles_df['timestamp'].dt.hour
        candles_df['minute'] = candles_df['timestamp'].dt.minute
        candles_df['time_decimal'] = candles_df['hour'] + candles_df['minute'] / 60
        
        start_decimal = int(start_time.split(':')[0]) + int(start_time.split(':')[1]) / 60
        end_decimal = int(end_time.split(':')[0]) + int(end_time.split(':')[1]) / 60
        
        if start_decimal <= end_decimal:
            # Same day session
            filtered_df = candles_df[
                (candles_df['time_decimal'] >= start_decimal) &
                (candles_df['time_decimal'] <= end_decimal)
            ]
        else:
            # Session crosses midnight
            filtered_df = candles_df[
                (candles_df['time_decimal'] >= start_decimal) |
                (candles_df['time_decimal'] <= end_decimal)
            ]
        
        return filtered_df.drop(['hour', 'minute', 'time_decimal'], axis=1)
    
    def add_volatility_filter(self, candles_df, atr_periods=14):
        """
        Add volatility-based filters
        """
        # Calculate ATR (Average True Range)
        candles_df['tr1'] = candles_df['high'] - candles_df['low']
        candles_df['tr2'] = abs(candles_df['high'] - candles_df['close'].shift())
        candles_df['tr3'] = abs(candles_df['low'] - candles_df['close'].shift())
        
        candles_df['true_range'] = candles_df[['tr1', 'tr2', 'tr3']].max(axis=1)
        candles_df['atr'] = candles_df['true_range'].rolling(atr_periods).mean()
        
        # Volatility percentile (for filtering low volatility periods)
        candles_df['atr_percentile'] = candles_df['atr'].rolling(100).rank(pct=True)
        
        # Volatility trend
        candles_df['atr_trend'] = candles_df['atr'] / candles_df['atr'].rolling(50).mean()
        
        # Clean up temporary columns
        candles_df.drop(['tr1', 'tr2', 'tr3'], axis=1, inplace=True)
        
        return candles_df
    
    def should_trade(self, current_candle, market_name='FTSE 100'):
        """
        Determine if conditions are right for trading
        Based on volatility and session filters
        """
        vol_config = self.config.get('volatility_filters', {})
        if not vol_config.get('enabled', False):
            return True, "Volatility filters disabled"
        
        # Check minimum ATR threshold
        min_atr = vol_config.get('min_atr_threshold', 0.5)
        if current_candle.get('atr', 0) < min_atr:
            return False, f"ATR {current_candle.get('atr', 0):.2f} below threshold {min_atr}"
        
        # Check consolidation filter
        if vol_config.get('consolidation_filter', False):
            atr_ratio = vol_config.get('consolidation_atr_ratio', 0.3)
            if current_candle.get('atr_trend', 1.0) < atr_ratio:
                return False, f"Low volatility period (ATR trend: {current_candle.get('atr_trend', 1.0):.2f})"
        
        return True, "All filters passed"
    
    def get_strategy_params(self, timeframe, market_name='FTSE 100'):
        """
        Get strategy parameters for specific timeframe and market
        """
        # Base parameters for timeframe
        base_params = self.config.get('strategy_by_timeframe', {}).get(timeframe, {})
        
        # Market-specific adjustments
        market_adj = self.config.get('market_adjustments', {}).get(market_name, {})
        
        # Apply market adjustments
        if market_adj:
            # Adjust for volatility
            vol_mult = market_adj.get('volatility_multiplier', 1.0)
            if 'stop_loss_pips' in base_params:
                base_params['stop_loss_pips'] = int(base_params['stop_loss_pips'] * vol_mult)
            if 'take_profit_pips' in base_params:
                base_params['take_profit_pips'] = int(base_params['take_profit_pips'] * vol_mult)
            
            # Adjust for spread
            spread_adj = market_adj.get('spread_adjustment', 1.0)
            base_params['spread_adjustment'] = spread_adj
        
        return base_params
    
    def get_risk_params(self, timeframe):
        """
        Get risk management parameters for timeframe
        """
        return self.config.get('risk_management', {}).get(timeframe, {
            'max_trades_per_day': 10,
            'max_drawdown_percent': 5.0,
            'position_size_percent': 2.0
        })