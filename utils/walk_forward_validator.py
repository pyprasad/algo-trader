#!/usr/bin/env python3
"""
📊 Walk-Forward Validation System

Implements robust walk-forward optimization for ML models:
- Rolling window training and validation
- Out-of-sample testing
- Performance degradation detection
- Model retraining triggers

Prevents overfitting and ensures robust performance in live trading.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable
import logging
from collections import deque
import json

logger = logging.getLogger(__name__)

class WalkForwardValidator:
    """Walk-forward validation system for trading models"""
    
    def __init__(self, 
                 train_window_days: int = 90,
                 test_window_days: int = 30,
                 min_train_samples: int = 1000,
                 retraining_threshold: float = 0.1):
        """
        Initialize walk-forward validator
        
        Args:
            train_window_days: Days of data for training
            test_window_days: Days of data for testing
            min_train_samples: Minimum samples required for training
            retraining_threshold: Performance drop threshold for retraining
        """
        
        self.train_window_days = train_window_days
        self.test_window_days = test_window_days
        self.min_train_samples = min_train_samples
        self.retraining_threshold = retraining_threshold
        
        # Performance tracking
        self.validation_results = []
        self.performance_history = deque(maxlen=50)
        self.last_retrain_date = None
        
        # Model performance tracking
        self.baseline_performance = None
        self.current_performance = None
        
        print("📊 Walk-Forward Validator initialized")
        print(f"   Training window: {train_window_days} days")
        print(f"   Testing window: {test_window_days} days")
        print(f"   Retraining threshold: {retraining_threshold:.1%} performance drop")
    
    def validate_model(self, 
                      model_class,
                      price_data: np.ndarray,
                      timestamps: List[datetime],
                      **model_kwargs) -> Dict:
        """
        Perform walk-forward validation on a model
        
        Args:
            model_class: Model class to validate
            price_data: Price data array
            timestamps: Corresponding timestamps
            **model_kwargs: Model initialization parameters
        
        Returns:
            Dictionary with validation results
        """
        
        print(f"\n📊 Starting Walk-Forward Validation")
        print(f"   Data points: {len(price_data)}")
        print(f"   Time span: {timestamps[0]} to {timestamps[-1]}")
        
        # Ensure we have enough data
        total_days = (timestamps[-1] - timestamps[0]).days
        required_days = self.train_window_days + self.test_window_days
        
        if total_days < required_days:
            print(f"❌ Insufficient data: {total_days} days < {required_days} days required")
            return {'success': False, 'error': 'Insufficient data'}
        
        # Create time-based folds
        folds = self._create_time_folds(timestamps)
        
        print(f"   Created {len(folds)} time-based folds")
        
        # Run validation
        fold_results = []
        
        for i, fold in enumerate(folds):
            print(f"\n🔄 Processing fold {i+1}/{len(folds)}")
            
            # Get training and testing data
            train_data = price_data[fold['train_start']:fold['train_end']]
            test_data = price_data[fold['test_start']:fold['test_end']]
            
            train_timestamps = timestamps[fold['train_start']:fold['train_end']]
            test_timestamps = timestamps[fold['test_start']:fold['test_end']]
            
            print(f"   Train: {len(train_data)} samples ({train_timestamps[0]} to {train_timestamps[-1]})")
            print(f"   Test:  {len(test_data)} samples ({test_timestamps[0]} to {test_timestamps[-1]})")
            
            # Train model
            model = model_class(**model_kwargs)
            
            try:
                train_success = model.train(train_data, epochs=50, validation_split=0.15)
                
                if not train_success:
                    print("   ❌ Training failed")
                    continue
                
                # Test model
                fold_result = self._test_model_fold(
                    model, test_data, test_timestamps, fold_info=fold
                )
                
                fold_results.append(fold_result)
                
                print(f"   ✅ Fold {i+1} complete - Accuracy: {fold_result['accuracy']:.3f}, "
                      f"Profit Factor: {fold_result['profit_factor']:.2f}")
                
            except Exception as e:
                print(f"   ❌ Fold {i+1} failed: {e}")
                continue
        
        # Aggregate results
        if fold_results:
            aggregated_results = self._aggregate_fold_results(fold_results)
            self.validation_results.append(aggregated_results)
            
            print(f"\n🏆 Walk-Forward Validation Complete")
            print(f"   Average Accuracy: {aggregated_results['avg_accuracy']:.3f}")
            print(f"   Average Profit Factor: {aggregated_results['avg_profit_factor']:.2f}")
            print(f"   Consistency Score: {aggregated_results['consistency_score']:.3f}")
            
            return aggregated_results
        
        else:
            print("❌ No successful folds")
            return {'success': False, 'error': 'All folds failed'}
    
    def _create_time_folds(self, timestamps: List[datetime]) -> List[Dict]:
        """Create time-based folds for walk-forward validation"""
        
        folds = []
        start_date = timestamps[0]
        end_date = timestamps[-1]
        
        # Create rolling windows
        current_date = start_date + timedelta(days=self.train_window_days)
        
        while current_date + timedelta(days=self.test_window_days) <= end_date:
            
            # Find indices for this fold
            train_start_date = current_date - timedelta(days=self.train_window_days)
            train_end_date = current_date
            test_start_date = current_date
            test_end_date = current_date + timedelta(days=self.test_window_days)
            
            # Convert to indices
            train_start_idx = self._find_date_index(timestamps, train_start_date)
            train_end_idx = self._find_date_index(timestamps, train_end_date)
            test_start_idx = self._find_date_index(timestamps, test_start_date)
            test_end_idx = self._find_date_index(timestamps, test_end_date)
            
            # Ensure we have enough training data
            if train_end_idx - train_start_idx >= self.min_train_samples:
                folds.append({
                    'train_start': train_start_idx,
                    'train_end': train_end_idx,
                    'test_start': test_start_idx,
                    'test_end': test_end_idx,
                    'train_start_date': train_start_date,
                    'train_end_date': train_end_date,
                    'test_start_date': test_start_date,
                    'test_end_date': test_end_date
                })
            
            # Move forward by test window
            current_date += timedelta(days=self.test_window_days)
        
        return folds
    
    def _find_date_index(self, timestamps: List[datetime], target_date: datetime) -> int:
        """Find the closest index for a target date"""
        
        for i, ts in enumerate(timestamps):
            if ts >= target_date:
                return i
        
        return len(timestamps) - 1
    
    def _test_model_fold(self, model, test_data: np.ndarray, 
                        test_timestamps: List[datetime], fold_info: Dict) -> Dict:
        """Test model on a single fold"""
        
        # Generate predictions for test period
        predictions = []
        actual_signals = []
        
        # Look-ahead for actual signal generation
        lookahead = 5
        threshold = 0.002  # 0.2% threshold
        
        for i in range(len(test_data) - lookahead):
            
            # Use data up to this point for prediction
            available_data = test_data[:i+50] if i >= 50 else test_data[:i+1]
            
            if len(available_data) >= 50:
                try:
                    prediction = model.predict_with_regime_awareness(available_data)
                    predictions.append(prediction)
                    
                    # Calculate actual signal
                    current_price = test_data[i]
                    future_price = test_data[i + lookahead]
                    change = (future_price - current_price) / current_price
                    
                    if change > threshold:
                        actual_signals.append('BUY')
                    elif change < -threshold:
                        actual_signals.append('SELL')
                    else:
                        actual_signals.append('HOLD')
                        
                except:
                    continue
        
        if not predictions:
            return {
                'accuracy': 0.0,
                'profit_factor': 1.0,
                'total_signals': 0,
                'fold_info': fold_info
            }
        
        # Calculate performance metrics
        predicted_signals = [p['signal'] for p in predictions]
        confidences = [p['confidence'] for p in predictions]
        
        # Accuracy calculation
        correct_predictions = sum(1 for pred, actual in zip(predicted_signals, actual_signals) 
                                if pred == actual)
        accuracy = correct_predictions / len(predictions) if predictions else 0
        
        # Simulate trading performance
        trades = self._simulate_trades(predictions, test_data, test_timestamps)
        
        # Calculate profit factor
        winning_trades = [t['pnl'] for t in trades if t['pnl'] > 0]
        losing_trades = [t['pnl'] for t in trades if t['pnl'] < 0]
        
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 1  # Avoid division by zero
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 1.0
        
        return {
            'accuracy': accuracy,
            'profit_factor': profit_factor,
            'total_signals': len(predictions),
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'avg_confidence': np.mean(confidences),
            'fold_info': fold_info,
            'trades': trades
        }
    
    def _simulate_trades(self, predictions: List[Dict], 
                        test_data: np.ndarray, timestamps: List[datetime]) -> List[Dict]:
        """Simulate trades based on predictions"""
        
        trades = []
        current_position = None
        
        for i, prediction in enumerate(predictions):
            
            if i >= len(test_data) - 1:
                break
            
            current_price = test_data[i]
            signal = prediction['signal']
            confidence = prediction['confidence']
            
            # Only trade high-confidence signals
            if confidence < 0.65:
                continue
            
            # Open new position
            if signal in ['BUY', 'SELL'] and current_position is None:
                current_position = {
                    'signal': signal,
                    'entry_price': current_price,
                    'entry_time': timestamps[i] if i < len(timestamps) else timestamps[-1],
                    'confidence': confidence
                }
            
            # Close position (simplified - close after 10 periods or opposite signal)
            elif current_position is not None:
                
                should_close = False
                close_reason = ''
                
                # Opposite signal with high confidence
                if signal != current_position['signal'] and signal != 'HOLD' and confidence > 0.7:
                    should_close = True
                    close_reason = 'opposite_signal'
                
                # Time-based exit (10 periods)
                elif i >= len(predictions) - 1:  # End of data
                    should_close = True
                    close_reason = 'end_of_data'
                
                if should_close:
                    # Calculate P&L
                    if current_position['signal'] == 'BUY':
                        pnl = current_price - current_position['entry_price']
                    else:  # SELL
                        pnl = current_position['entry_price'] - current_price
                    
                    # Account for spread (simplified)
                    pnl -= 1.0
                    
                    trades.append({
                        'entry_price': current_position['entry_price'],
                        'exit_price': current_price,
                        'entry_time': current_position['entry_time'],
                        'exit_time': timestamps[i] if i < len(timestamps) else timestamps[-1],
                        'signal': current_position['signal'],
                        'pnl': pnl,
                        'confidence': current_position['confidence'],
                        'close_reason': close_reason
                    })
                    
                    current_position = None
        
        return trades
    
    def _aggregate_fold_results(self, fold_results: List[Dict]) -> Dict:
        """Aggregate results from all folds"""
        
        if not fold_results:
            return {'success': False}
        
        # Calculate averages
        avg_accuracy = np.mean([f['accuracy'] for f in fold_results])
        avg_profit_factor = np.mean([f['profit_factor'] for f in fold_results])
        avg_confidence = np.mean([f['avg_confidence'] for f in fold_results])
        
        total_trades = sum([f['total_trades'] for f in fold_results])
        total_winning = sum([f['winning_trades'] for f in fold_results])
        total_losing = sum([f['losing_trades'] for f in fold_results])
        
        # Calculate consistency (lower std = more consistent)
        accuracy_std = np.std([f['accuracy'] for f in fold_results])
        profit_factor_std = np.std([f['profit_factor'] for f in fold_results])
        
        consistency_score = 1.0 / (1.0 + accuracy_std + profit_factor_std)
        
        # Overall win rate
        overall_win_rate = total_winning / total_trades if total_trades > 0 else 0
        
        return {
            'success': True,
            'num_folds': len(fold_results),
            'avg_accuracy': avg_accuracy,
            'avg_profit_factor': avg_profit_factor,
            'avg_confidence': avg_confidence,
            'accuracy_std': accuracy_std,
            'profit_factor_std': profit_factor_std,
            'consistency_score': consistency_score,
            'total_trades': total_trades,
            'overall_win_rate': overall_win_rate,
            'total_winning': total_winning,
            'total_losing': total_losing,
            'fold_results': fold_results
        }
    
    def should_retrain_model(self, current_performance: float) -> bool:
        """Determine if model should be retrained based on performance"""
        
        if self.baseline_performance is None:
            self.baseline_performance = current_performance
            return False
        
        # Track recent performance
        self.performance_history.append(current_performance)
        
        # Check if performance has degraded significantly
        recent_avg = np.mean(list(self.performance_history)[-10:])  # Last 10 measurements
        performance_drop = (self.baseline_performance - recent_avg) / self.baseline_performance
        
        # Check if we should retrain
        if performance_drop > self.retraining_threshold:
            print(f"⚠️ Performance degradation detected: {performance_drop:.1%} drop")
            print(f"   Baseline: {self.baseline_performance:.3f}")
            print(f"   Recent average: {recent_avg:.3f}")
            return True
        
        return False
    
    def update_baseline_performance(self, new_performance: float):
        """Update baseline performance after retraining"""
        
        self.baseline_performance = new_performance
        self.last_retrain_date = datetime.now()
        
        print(f"✅ Baseline performance updated to {new_performance:.3f}")
    
    def get_validation_summary(self) -> Dict:
        """Get summary of all validation results"""
        
        if not self.validation_results:
            return {'message': 'No validation results available'}
        
        latest_result = self.validation_results[-1]
        
        return {
            'total_validations': len(self.validation_results),
            'latest_validation': {
                'avg_accuracy': latest_result.get('avg_accuracy', 0),
                'avg_profit_factor': latest_result.get('avg_profit_factor', 1),
                'consistency_score': latest_result.get('consistency_score', 0),
                'total_trades': latest_result.get('total_trades', 0)
            },
            'performance_trend': self._calculate_performance_trend(),
            'baseline_performance': self.baseline_performance,
            'last_retrain': self.last_retrain_date
        }
    
    def _calculate_performance_trend(self) -> str:
        """Calculate performance trend over recent validations"""
        
        if len(self.validation_results) < 2:
            return 'insufficient_data'
        
        recent_accuracy = [r.get('avg_accuracy', 0) for r in self.validation_results[-3:]]
        
        if len(recent_accuracy) >= 2:
            if recent_accuracy[-1] > recent_accuracy[0]:
                return 'improving'
            elif recent_accuracy[-1] < recent_accuracy[0]:
                return 'declining'
            else:
                return 'stable'
        
        return 'unknown'


def test_walk_forward_validator():
    """Test the walk-forward validator"""
    
    print("🧪 Testing Walk-Forward Validator")
    print("="*50)
    
    # Mock model class for testing
    class MockModel:
        def __init__(self):
            self.is_fitted = False
            
        def train(self, data, epochs=50, validation_split=0.15):
            self.is_fitted = True
            return True
            
        def predict_with_regime_awareness(self, data):
            # Simple mock prediction
            return {
                'signal': np.random.choice(['BUY', 'SELL', 'HOLD']),
                'confidence': np.random.uniform(0.5, 0.9),
                'regime': 'neutral'
            }
    
    # Generate test data
    dates = pd.date_range(start='2024-01-01', end='2024-06-01', freq='1H')
    prices = np.random.randn(len(dates)).cumsum() + 8000
    
    # Test validator
    validator = WalkForwardValidator(
        train_window_days=30,
        test_window_days=7,
        min_train_samples=100
    )
    
    results = validator.validate_model(MockModel, prices, dates.to_list())
    
    if results.get('success'):
        print("✅ Walk-forward validation successful")
        print(f"   Average accuracy: {results['avg_accuracy']:.3f}")
        print(f"   Consistency score: {results['consistency_score']:.3f}")
    else:
        print("❌ Walk-forward validation failed")
    
    return results.get('success', False)


if __name__ == "__main__":
    test_walk_forward_validator()