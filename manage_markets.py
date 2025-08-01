#!/usr/bin/env python3
# manage_markets.py - Easy market management utility

import sys
import os
sys.path.append(os.path.abspath('.'))

from utils.market_config_loader import MarketConfigLoader

def main():
    """Interactive market management"""
    config_loader = MarketConfigLoader()
    
    while True:
        print("\n" + "="*60)
        print("🏪 MARKET MANAGEMENT UTILITY")
        print("="*60)
        
        print("1. Show current configuration")
        print("2. List all available markets")
        print("3. List active markets")
        print("4. Add market to active list")
        print("5. Remove market from active list")
        print("6. Test market configuration")
        print("0. Exit")
        
        choice = input("\nEnter your choice (0-6): ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            config_loader.print_market_summary()
        elif choice == "2":
            markets = config_loader.get_available_markets()
            print(f"\n📊 Available Markets ({len(markets)}):")
            for i, market in enumerate(markets, 1):
                config = config_loader.get_market_config(market)
                epic = config.get('epic', 'N/A') if config else 'N/A'
                sector = config.get('sector', 'N/A') if config else 'N/A'
                print(f"  {i:2d}. {market} ({epic}) - {sector}")
        elif choice == "3":
            markets = config_loader.get_active_markets()
            print(f"\n🎯 Active Markets ({len(markets)}):")
            for i, market in enumerate(markets, 1):
                config = config_loader.get_market_config(market)
                trade_size = config.get('trade_size', 'N/A') if config else 'N/A'
                currency = config.get('currency', 'N/A') if config else 'N/A'
                print(f"  {i:2d}. {market} - Size: {trade_size} {currency}")
        elif choice == "4":
            available_markets = config_loader.get_available_markets()
            active_markets = config_loader.get_active_markets()
            inactive_markets = [m for m in available_markets if m not in active_markets]
            
            if not inactive_markets:
                print("⚠️ All available markets are already active!")
                continue
            
            print(f"\n📋 Inactive Markets ({len(inactive_markets)}):")
            for i, market in enumerate(inactive_markets, 1):
                config = config_loader.get_market_config(market)
                epic = config.get('epic', 'N/A') if config else 'N/A'
                sector = config.get('sector', 'N/A') if config else 'N/A'
                print(f"  {i:2d}. {market} ({epic}) - {sector}")
            
            try:
                selection = int(input(f"\nSelect market to add (1-{len(inactive_markets)}): ")) - 1
                if 0 <= selection < len(inactive_markets):
                    market_to_add = inactive_markets[selection]
                    config_loader.add_market_to_active(market_to_add)
                else:
                    print("❌ Invalid selection!")
            except ValueError:
                print("❌ Please enter a valid number!")
        elif choice == "5":
            active_markets = config_loader.get_active_markets()
            
            if not active_markets:
                print("⚠️ No active markets to remove!")
                continue
            
            print(f"\n🎯 Active Markets ({len(active_markets)}):")
            for i, market in enumerate(active_markets, 1):
                config = config_loader.get_market_config(market)
                trade_size = config.get('trade_size', 'N/A') if config else 'N/A'
                print(f"  {i:2d}. {market} - Size: {trade_size}")
            
            try:
                selection = int(input(f"\nSelect market to remove (1-{len(active_markets)}): ")) - 1
                if 0 <= selection < len(active_markets):
                    market_to_remove = active_markets[selection]
                    config_loader.remove_market_from_active(market_to_remove)
                else:
                    print("❌ Invalid selection!")
            except ValueError:
                print("❌ Please enter a valid number!")
        elif choice == "6":
            print("\n🧪 Testing market configuration...")
            from test_config_system import test_config_system
            test_config_system()
        else:
            print("❌ Invalid choice! Please enter 0-6.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)