#!/usr/bin/env python3
"""
🔧 System Mode Manager

Manages different trading system modes (Conservative, Moderate, Aggressive, Custom)
based on configuration flags. Allows easy switching between risk profiles.

Usage:
    from utils.system_mode_manager import get_system_mode_config
    
    config = get_system_mode_config()
    print(f"Current mode: {config['mode']}")
    print(f"Signal confidence required: {config['min_signal_confidence']:.0%}")
"""

import yaml
import os
from typing import Dict, Any
from datetime import timedelta

class SystemModeManager:
    """Manages different trading system modes and configurations"""
    
    def __init__(self, config_path: str = "configs/global.yaml"):
        """Initialize with configuration file path"""
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading config from {self.config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if file loading fails"""
        return {
            'professional_trading': {
                'enabled': True,
                'system_mode': 'moderate',
                'modes': {
                    'moderate': {
                        'min_signal_confidence': 0.65,
                        'analysis_interval_minutes': 3,
                        'max_trades_per_hour': 2,
                        'daily_loss_limit': 300,
                        'trade_frequency': 'medium'
                    }
                }
            }
        }
    
    def get_current_mode_config(self) -> Dict[str, Any]:
        """Get configuration for currently selected mode"""
        try:
            prof_config = self.config.get('professional_trading', {})
            current_mode = prof_config.get('system_mode', 'moderate')
            modes = prof_config.get('modes', {})
            
            if current_mode not in modes:
                print(f"⚠️ Unknown mode '{current_mode}', falling back to 'moderate'")
                current_mode = 'moderate'
            
            mode_config = modes.get(current_mode, modes.get('moderate', {}))
            
            # Add mode name and metadata
            result = mode_config.copy()
            result['mode'] = current_mode
            result['enabled'] = prof_config.get('enabled', True)
            
            return result
            
        except Exception as e:
            print(f"❌ Error getting mode config: {e}")
            return self._get_default_mode_config()
    
    def _get_default_mode_config(self) -> Dict[str, Any]:
        """Default mode configuration"""
        return {
            'mode': 'moderate',
            'enabled': True,
            'min_signal_confidence': 0.65,
            'analysis_interval_minutes': 3,
            'max_trades_per_hour': 2,
            'daily_loss_limit': 300,
            'trade_frequency': 'medium'
        }
    
    def get_available_modes(self) -> Dict[str, Dict]:
        """Get all available trading modes"""
        try:
            prof_config = self.config.get('professional_trading', {})
            return prof_config.get('modes', {})
        except Exception as e:
            print(f"❌ Error getting available modes: {e}")
            return {'moderate': self._get_default_mode_config()}
    
    def switch_mode(self, new_mode: str) -> bool:
        """Switch to a different trading mode"""
        available_modes = self.get_available_modes()
        
        if new_mode not in available_modes:
            print(f"❌ Mode '{new_mode}' not available. Available modes: {list(available_modes.keys())}")
            return False
        
        try:
            # Update config in memory
            self.config['professional_trading']['system_mode'] = new_mode
            
            # Write to file
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            
            print(f"✅ Switched to '{new_mode}' mode")
            return True
            
        except Exception as e:
            print(f"❌ Error switching to mode '{new_mode}': {e}")
            return False
    
    def get_mode_comparison(self) -> str:
        """Get a formatted comparison of all modes"""
        modes = self.get_available_modes()
        current_mode = self.get_current_mode_config()['mode']
        
        comparison = "\n🔧 AVAILABLE TRADING SYSTEM MODES:\n"
        comparison += "=" * 60 + "\n\n"
        
        # Header
        comparison += f"{'Mode':<12} {'Confidence':<11} {'Frequency':<9} {'Max/Hour':<9} {'Daily Loss':<11} {'Status'}\n"
        comparison += "-" * 60 + "\n"
        
        for mode_name, mode_config in modes.items():
            confidence = f"{mode_config.get('min_signal_confidence', 0.65):.0%}"
            interval = f"{mode_config.get('analysis_interval_minutes', 3)}min"
            max_trades = f"{mode_config.get('max_trades_per_hour', 2)}/h"
            daily_loss = f"£{mode_config.get('daily_loss_limit', 300)}"
            status = "🟢 ACTIVE" if mode_name == current_mode else "⚪ Available"
            
            comparison += f"{mode_name:<12} {confidence:<11} {interval:<9} {max_trades:<9} {daily_loss:<11} {status}\n"
        
        comparison += "\n📊 MODE DESCRIPTIONS:\n"
        comparison += "• Conservative: Ultra-safe, minimal trades, capital preservation focus\n"
        comparison += "• Moderate: Balanced risk-reward, good for most users\n" 
        comparison += "• Aggressive: Higher frequency, more opportunities, increased risk\n"
        comparison += "• Custom: User-defined parameters\n"
        
        comparison += f"\n🎯 Current Mode: {current_mode.upper()}\n"
        
        return comparison
    
    def validate_mode_config(self, mode_name: str) -> bool:
        """Validate that a mode configuration is complete and valid"""
        modes = self.get_available_modes()
        
        if mode_name not in modes:
            return False
        
        mode_config = modes[mode_name]
        required_fields = [
            'min_signal_confidence',
            'analysis_interval_minutes', 
            'max_trades_per_hour',
            'daily_loss_limit'
        ]
        
        for field in required_fields:
            if field not in mode_config:
                print(f"❌ Mode '{mode_name}' missing required field: {field}")
                return False
        
        # Validate ranges
        if not (0.5 <= mode_config['min_signal_confidence'] <= 0.95):
            print(f"❌ Invalid signal confidence: {mode_config['min_signal_confidence']}")
            return False
            
        if not (1 <= mode_config['analysis_interval_minutes'] <= 10):
            print(f"❌ Invalid analysis interval: {mode_config['analysis_interval_minutes']}")
            return False
            
        if not (1 <= mode_config['max_trades_per_hour'] <= 10):
            print(f"❌ Invalid max trades per hour: {mode_config['max_trades_per_hour']}")
            return False
            
        if not (50 <= mode_config['daily_loss_limit'] <= 1000):
            print(f"❌ Invalid daily loss limit: {mode_config['daily_loss_limit']}")
            return False
        
        return True

# Global instance
_system_mode_manager = None

def get_system_mode_manager() -> SystemModeManager:
    """Get global system mode manager instance"""
    global _system_mode_manager
    if _system_mode_manager is None:
        _system_mode_manager = SystemModeManager()
    return _system_mode_manager

def get_system_mode_config() -> Dict[str, Any]:
    """Get current system mode configuration (convenience function)"""
    return get_system_mode_manager().get_current_mode_config()

def switch_system_mode(mode: str) -> bool:
    """Switch system mode (convenience function)"""
    return get_system_mode_manager().switch_mode(mode)

def show_mode_comparison() -> str:
    """Show comparison of all available modes"""
    return get_system_mode_manager().get_mode_comparison()

# CLI Interface Functions
def main():
    """Command-line interface for mode management"""
    import sys
    
    manager = get_system_mode_manager()
    
    if len(sys.argv) == 1:
        # Show current config
        print(manager.get_mode_comparison())
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        print(manager.get_mode_comparison())
        
    elif command == "switch":
        if len(sys.argv) < 3:
            print("❌ Usage: python system_mode_manager.py switch <mode>")
            print("Available modes:", list(manager.get_available_modes().keys()))
            return
            
        new_mode = sys.argv[2].lower()
        if manager.switch_mode(new_mode):
            print(f"✅ Successfully switched to '{new_mode}' mode")
            print("\n" + manager.get_mode_comparison())
        
    elif command == "list":
        modes = manager.get_available_modes()
        print(f"\n🔧 Available modes: {', '.join(modes.keys())}")
        for mode, config in modes.items():
            print(f"   {mode}: {config}")
            
    else:
        print("❌ Unknown command. Available commands:")
        print("   status  - Show current mode and all available modes")
        print("   switch <mode> - Switch to a different mode")  
        print("   list    - List all available modes with settings")

if __name__ == "__main__":
    main()