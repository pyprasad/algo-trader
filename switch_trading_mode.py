#!/usr/bin/env python3
"""
🔧 Trading Mode Switcher

Easy command-line tool to switch between trading system modes.

Usage:
    python switch_trading_mode.py                    # Show current status
    python switch_trading_mode.py conservative       # Switch to conservative
    python switch_trading_mode.py moderate          # Switch to moderate  
    python switch_trading_mode.py aggressive        # Switch to aggressive
    python switch_trading_mode.py custom            # Switch to custom
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from utils.system_mode_manager import get_system_mode_manager

def main():
    """Main function for mode switching"""
    manager = get_system_mode_manager()
    
    print("🔧 Trading System Mode Manager")
    print("=" * 50)
    
    if len(sys.argv) == 1:
        # Show current status
        print(manager.get_mode_comparison())
        print("\n💡 Usage:")
        print("   python switch_trading_mode.py conservative")
        print("   python switch_trading_mode.py moderate")
        print("   python switch_trading_mode.py aggressive")
        print("   python switch_trading_mode.py custom")
        return
    
    # Get requested mode
    requested_mode = sys.argv[1].lower()
    available_modes = list(manager.get_available_modes().keys())
    
    if requested_mode not in available_modes:
        print(f"❌ Invalid mode: '{requested_mode}'")
        print(f"Available modes: {', '.join(available_modes)}")
        return
    
    # Get current mode
    current_config = manager.get_current_mode_config()
    current_mode = current_config['mode']
    
    if requested_mode == current_mode:
        print(f"✅ Already in '{requested_mode}' mode")
        print(f"\nCurrent settings:")
        print(f"   Signal Confidence: {current_config['min_signal_confidence']:.0%}")
        print(f"   Analysis Interval: {current_config['analysis_interval_minutes']} minutes")
        print(f"   Max Trades/Hour: {current_config['max_trades_per_hour']}")
        print(f"   Daily Loss Limit: £{current_config['daily_loss_limit']}")
        return
    
    # Confirm the switch
    print(f"Current mode: {current_mode}")
    print(f"Switching to: {requested_mode}")
    print("\n🔍 Mode comparison:")
    
    modes = manager.get_available_modes()
    current_mode_config = modes[current_mode]
    new_mode_config = modes[requested_mode]
    
    print(f"\n{'Setting':<20} {'Current (' + current_mode + ')':<15} {'New (' + requested_mode + ')':<15} {'Change'}")
    print("-" * 70)
    
    # Compare settings
    comparisons = [
        ('Signal Confidence', 
         f"{current_mode_config['min_signal_confidence']:.0%}",
         f"{new_mode_config['min_signal_confidence']:.0%}",
         current_mode_config['min_signal_confidence'] - new_mode_config['min_signal_confidence']),
        
        ('Analysis Interval',
         f"{current_mode_config['analysis_interval_minutes']}min",
         f"{new_mode_config['analysis_interval_minutes']}min", 
         current_mode_config['analysis_interval_minutes'] - new_mode_config['analysis_interval_minutes']),
        
        ('Max Trades/Hour',
         str(current_mode_config['max_trades_per_hour']),
         str(new_mode_config['max_trades_per_hour']),
         current_mode_config['max_trades_per_hour'] - new_mode_config['max_trades_per_hour']),
        
        ('Daily Loss Limit',
         f"£{current_mode_config['daily_loss_limit']}",
         f"£{new_mode_config['daily_loss_limit']}",
         current_mode_config['daily_loss_limit'] - new_mode_config['daily_loss_limit'])
    ]
    
    for setting, current_val, new_val, diff in comparisons:
        if isinstance(diff, float):
            change_indicator = "↑" if diff < 0 else ("↓" if diff > 0 else "=")
        else:
            change_indicator = "↑" if diff < 0 else ("↓" if diff > 0 else "=")
        
        print(f"{setting:<20} {current_val:<15} {new_val:<15} {change_indicator}")
    
    # Ask for confirmation
    response = input(f"\n❓ Switch to '{requested_mode}' mode? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        if manager.switch_mode(requested_mode):
            print(f"\n✅ Successfully switched to '{requested_mode}' mode!")
            
            # Show impact
            print(f"\n🎯 What this means:")
            if requested_mode == 'conservative':
                print("   • Ultra-safe trading with minimal frequency")
                print("   • Only highest confidence signals (75%+)")
                print("   • Maximum 1 trade per hour per market")
                print("   • Perfect for beginners and capital preservation")
            elif requested_mode == 'moderate':
                print("   • Balanced risk-reward approach")
                print("   • Good signal confidence (65%+)")
                print("   • Up to 2 trades per hour per market")
                print("   • Recommended for most users")
            elif requested_mode == 'aggressive':
                print("   • More active trading for higher returns")
                print("   • Moderate signal confidence (60%+)")
                print("   • Up to 3 trades per hour per market")
                print("   • For experienced users comfortable with risk")
            elif requested_mode == 'custom':
                print("   • Your personalized settings")
                print("   • Edit configs/global.yaml to customize")
            
            print(f"\n🔄 Restart your trading system to apply the new mode")
            
        else:
            print(f"❌ Failed to switch to '{requested_mode}' mode")
    else:
        print("❌ Mode switch cancelled")

if __name__ == "__main__":
    main()