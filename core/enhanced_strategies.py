# core/enhanced_strategies.py

import pandas as pd
import numpy as np
from typing import Dict, Tuple
import yaml

class EnhancedTradingStrategies:
    """
    Enhanced trading strategies optimized for different timeframes
    All strategies are configurable and maintainable
    """
    
    def __init__(self, config_path='configs/timeframe_config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def supertrend_strategy(self, candles_df, params=None):
        """
        SuperTrend strategy - works best on 1-15 minute timeframes
        Trend-following algorithm
        """
        if params is None:
            params = {'atr_period': 14, 'multiplier': 3.0}
        
        df = candles_df.copy()
        
        # Calculate ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        df['atr'] = df['tr'].rolling(params['atr_period']).mean()
        
        # SuperTrend calculation
        hl_avg = (df['high'] + df['low']) / 2
        df['upper_band'] = hl_avg + (params['multiplier'] * df['atr'])
        df['lower_band'] = hl_avg - (params['multiplier'] * df['atr'])
        
        # Initialize SuperTrend
        df['supertrend'] = 0.0
        df['direction'] = 1
        df['signal'] = 'HOLD'
        
        for i in range(1, len(df)):
            # Update SuperTrend logic
            if df['close'].iloc[i] > df['upper_band'].iloc[i-1]:
                df.loc[df.index[i], 'supertrend'] = df['lower_band'].iloc[i]
                df.loc[df.index[i], 'direction'] = 1
            elif df['close'].iloc[i] < df['lower_band'].iloc[i-1]:
                df.loc[df.index[i], 'supertrend'] = df['upper_band'].iloc[i]
                df.loc[df.index[i], 'direction'] = -1
            else:
                df.loc[df.index[i], 'supertrend'] = df['supertrend'].iloc[i-1]
                df.loc[df.index[i], 'direction'] = df['direction'].iloc[i-1]
            
            # Generate signals on direction change
            if i > 1:
                if df['direction'].iloc[i] == 1 and df['direction'].iloc[i-1] == -1:
                    df.loc[df.index[i], 'signal'] = 'BUY'
                elif df['direction'].iloc[i] == -1 and df['direction'].iloc[i-1] == 1:
                    df.loc[df.index[i], 'signal'] = 'SELL'
        
        return df
    
    def ma_crossover_strategy(self, candles_df, params=None):
        """
        Moving Average Crossover - works best on 5-30 minute timeframes
        Simple but effective trend following
        """
        if params is None:
            params = {'fast_ma': 10, 'slow_ma': 50}
        
        df = candles_df.copy()
        
        # Calculate moving averages
        df['ma_fast'] = df['close'].rolling(params['fast_ma']).mean()
        df['ma_slow'] = df['close'].rolling(params['slow_ma']).mean()
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # Crossover detection
        for i in range(1, len(df)):
            if (df['ma_fast'].iloc[i] > df['ma_slow'].iloc[i] and 
                df['ma_fast'].iloc[i-1] <= df['ma_slow'].iloc[i-1]):
                df.loc[df.index[i], 'signal'] = 'BUY'
            elif (df['ma_fast'].iloc[i] < df['ma_slow'].iloc[i] and 
                  df['ma_fast'].iloc[i-1] >= df['ma_slow'].iloc[i-1]):
                df.loc[df.index[i], 'signal'] = 'SELL'
        
        # Add trend strength
        df['trend_strength'] = abs(df['ma_fast'] - df['ma_slow']) / df['ma_slow']
        
        return df
    
    def rsi_trend_strategy(self, candles_df, params=None):
        """
        RSI + Trend Filter - works best on 15-60 minute timeframes
        Mean reversion with trend confirmation
        """
        if params is None:
            params = {
                'rsi_period': 14, 
                'rsi_overbought': 80, 
                'rsi_oversold': 20,
                'trend_ema': 200
            }
        
        df = candles_df.copy()
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(params['rsi_period']).mean()
        avg_loss = loss.rolling(params['rsi_period']).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Trend filter
        df['trend_ema'] = df['close'].rolling(params['trend_ema']).mean()
        df['in_uptrend'] = df['close'] > df['trend_ema']
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        for i in range(1, len(df)):
            rsi_current = df['rsi'].iloc[i]
            in_uptrend = df['in_uptrend'].iloc[i]
            
            # Buy oversold in uptrend
            if rsi_current < params['rsi_oversold'] and in_uptrend:
                df.loc[df.index[i], 'signal'] = 'BUY'
            # Sell overbought in downtrend  
            elif rsi_current > params['rsi_overbought'] and not in_uptrend:
                df.loc[df.index[i], 'signal'] = 'SELL'
        
        return df
    
    def bollinger_rsi_strategy(self, candles_df, params=None):
        """
        Bollinger Bands + RSI - works best on 30 minute to 4 hour timeframes
        Volatility breakout with momentum confirmation
        """
        if params is None:
            params = {
                'bollinger_period': 20,
                'bollinger_std': 2.0,
                'rsi_period': 14,
                'rsi_buy': 30,
                'rsi_sell': 70
            }
        
        df = candles_df.copy()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(params['bollinger_period']).mean()
        bb_std = df['close'].rolling(params['bollinger_period']).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * params['bollinger_std'])
        df['bb_lower'] = df['bb_middle'] - (bb_std * params['bollinger_std'])
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(params['rsi_period']).mean()
        avg_loss = loss.rolling(params['rsi_period']).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        for i in range(1, len(df)):
            price = df['close'].iloc[i]
            rsi = df['rsi'].iloc[i]
            bb_lower = df['bb_lower'].iloc[i]
            bb_upper = df['bb_upper'].iloc[i]
            
            # Buy: Price touches lower band + RSI oversold
            if price <= bb_lower and rsi < params['rsi_buy']:
                df.loc[df.index[i], 'signal'] = 'BUY'
            # Sell: Price touches upper band + RSI overbought
            elif price >= bb_upper and rsi > params['rsi_sell']:
                df.loc[df.index[i], 'signal'] = 'SELL'
        
        return df
    
    def adaptive_strategy(self, candles_df, timeframe, market_name='FTSE 100'):
        """
        Automatically select and configure strategy based on timeframe and market
        This is the main entry point for configurable trading
        """
        # Get strategy parameters from config
        strategy_params = self.get_strategy_params(timeframe, market_name)
        algorithm = strategy_params.get('algorithm', 'ma_crossover')
        
        # Apply the appropriate strategy
        if algorithm == 'supertrend':
            params = {
                'atr_period': strategy_params.get('atr_period', 14),
                'multiplier': strategy_params.get('multiplier', 3.0)
            }
            result_df = self.supertrend_strategy(candles_df, params)
            
        elif algorithm == 'ma_crossover':
            params = {
                'fast_ma': strategy_params.get('fast_ma', 10),
                'slow_ma': strategy_params.get('slow_ma', 50)
            }
            result_df = self.ma_crossover_strategy(candles_df, params)
            
        elif algorithm == 'rsi_trend':
            params = {
                'rsi_period': strategy_params.get('rsi_period', 14),
                'rsi_overbought': strategy_params.get('rsi_overbought', 80),
                'rsi_oversold': strategy_params.get('rsi_oversold', 20),
                'trend_ema': strategy_params.get('trend_ema', 200)
            }
            result_df = self.rsi_trend_strategy(candles_df, params)
            
        elif algorithm == 'bollinger_rsi':
            params = {
                'bollinger_period': strategy_params.get('bollinger_period', 20),
                'bollinger_std': strategy_params.get('bollinger_std', 2.0),
                'rsi_period': strategy_params.get('rsi_period', 14),
                'rsi_buy': strategy_params.get('rsi_buy', 30),
                'rsi_sell': strategy_params.get('rsi_sell', 70)
            }
            result_df = self.bollinger_rsi_strategy(candles_df, params)
        
        else:
            # Default to MA crossover
            result_df = self.ma_crossover_strategy(candles_df)
        
        # Add strategy metadata
        result_df['strategy_used'] = algorithm
        result_df['timeframe'] = timeframe
        
        return result_df
    
    def get_strategy_params(self, timeframe, market_name='FTSE 100'):
        """
        Get strategy parameters from config file
        """
        # Base parameters for timeframe
        base_params = self.config.get('strategy_by_timeframe', {}).get(timeframe, {})
        
        # Market-specific adjustments
        market_adj = self.config.get('market_adjustments', {}).get(market_name, {})
        
        # Apply market adjustments
        if market_adj:
            vol_mult = market_adj.get('volatility_multiplier', 1.0)
            if 'stop_loss_pips' in base_params:
                base_params['stop_loss_pips'] = int(base_params['stop_loss_pips'] * vol_mult)
            if 'take_profit_pips' in base_params:
                base_params['take_profit_pips'] = int(base_params['take_profit_pips'] * vol_mult)
        
        return base_params
    
    def calculate_stop_loss_take_profit(self, entry_price, direction, candles_df, params):
        """
        Calculate dynamic stop loss and take profit based on strategy and market conditions
        """
        if 'stop_loss_atr' in params and 'take_profit_atr' in params:
            # ATR-based SL/TP
            current_atr = candles_df['atr'].iloc[-1] if 'atr' in candles_df.columns else 10
            sl_distance = current_atr * params['stop_loss_atr']
            tp_distance = current_atr * params['take_profit_atr']
        else:
            # Fixed pip-based SL/TP
            sl_distance = params.get('stop_loss_pips', 15)
            tp_distance = params.get('take_profit_pips', 30)
        
        if direction == 'BUY':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        
        return stop_loss, take_profit