#!/usr/bin/env python3
"""
🧹 Codebase Cleanup Script

Removes redundant, obsolete, and duplicate files to create a clean,
production-ready codebase focused on the multi-profile trading system.

SAFETY: Creates backup before deletion and provides dry-run mode.
"""

import os
import shutil
from datetime import datetime
import argparse

def create_backup():
    """Create backup of current state"""
    backup_name = f"backup_before_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = f"../{backup_name}"
    
    print(f"📦 Creating backup: {backup_path}")
    
    # Create backup directory
    os.makedirs(backup_path, exist_ok=True)
    
    # Copy important files to backup
    backup_files = [
        "README.md", "CLAUDE.md", "requirements.txt",
        "configs/", "core/", "data/", "scripts/", "utils/", 
        "models/", "runners/", "reports/"
    ]
    
    for item in backup_files:
        if os.path.exists(item):
            if os.path.isdir(item):
                shutil.copytree(item, os.path.join(backup_path, item), dirs_exist_ok=True)
            else:
                shutil.copy2(item, backup_path)
    
    print(f"✅ Backup created: {backup_path}")
    return backup_path

def cleanup_files(dry_run=True):
    """Execute the cleanup based on analysis"""
    
    # Files to delete organized by category
    cleanup_plan = {
        "Redundant Backtest Files": [
            "august_8_clean_account_simulation.py",
            "august_8_diagnostic_backtest.py",  
            "august_8_realistic_pnl_analysis.py",
            "backtest_actual_system.py",
            "backtest_actual_system_old_data.py",
            "backtest_advanced_ml_comparison.py",
            "backtest_august_8_fixes.py",
            "backtest_august_8_smart_money.py",
            "backtest_august_8_with_ml.py",
            "backtest_ml_simulation.py",
            "backtest_old_ftse_all_modes.py",
            "backtest_smart_money_enhancement.py",
            "backtest_engine.py"
        ],
        
        "Excessive Documentation Files": [
            "ADVANCED_FEATURES.md",
            "ALGO_ENHANCEMENTS_README.md",
            "AUGUST_8TH_ML_BACKTEST_SUMMARY.md",
            "COMPREHENSIVE_PNL_ANALYSIS_REPORT.md",
            "CRITICAL_FIXES_SUMMARY.md",
            "DYNAMIC_POSITION_MANAGEMENT.md",
            "ECONOMIC_CALENDAR_IMPLEMENTATION_COMPLETE.md",
            "EMERGENCY_CAPITAL_PROTECTION.md",
            "ENHANCED_SYSTEM_GUIDE.md",
            "LOSS_REDUCTION_IMPLEMENTATION.md",
            "MULTI_MARKET_GUIDE.md",
            "MULTI_PROFILE_IMPLEMENTATION_COMPLETE.md",
            "PENDING_TRADE_FIX.md",
            "SMART_MONEY_IMPLEMENTATION_COMPLETE.md",
            "TRADE_STREAMING_FIX.md",
            "TRADING_ANALYSIS_REPORT.md",
            "TRADING_LOGIC_README.md",
            "TRADING_MODE_GUIDE.md",
            "trading_system_comprehensive_review.md"
        ],
        
        "Obsolete Test Files": [
            "test_account_streaming.py",
            "test_after_hours.py",
            "test_asset_config.py",
            "test_balance_verification.py",
            "test_config_system.py",
            "test_critical_fixes.py",
            "test_dynamic_position_management.py",
            "test_economic_calendar_integration.py",
            "test_enhanced_system.py",
            "test_ml_training.py",
            "test_multi_market.py",
            "test_pending_trade_handling.py",
            "test_professional_improvements.py",
            "test_smart_money_integration.py",
            "test_streaming_brief.py",
            "test_streaming_fix.py",
            "test_trade_streaming_fix.py"
        ],
        
        "Legacy Demo/Debug Files": [
            "demo_config_system.py",
            "demo_enhanced_system.py",
            "demo_live_account.py",
            "demo_multi_market.py",
            "fix_corrupted_trades.py",
            "investigate_ftse_stops.py",
            "quick_pnl_analysis.py",
            "scripts/debug_signal_log.py"
        ],
        
        "Redundant Utility Files": [
            "manage_markets.py",
            "start_autonomous_trading.py",
            "strategy_comparison.py",
            "switch_trading_mode.py",
            "system_health_check.py"
        ],
        
        "Old Data Files": [
            "08Aug2025_data.csv",
            "PNL_ANALYSIS_SUMMARY.csv"
        ],
        
        "Legacy/Unused Files": [
            "INTEGRATION_EXAMPLE.py",
            "run_focused_backtest.py",
            "train_ml_for_august_backtest.py"
        ]
    }
    
    # Additional config files to clean up
    config_cleanup = {
        "Redundant Config Files": [
            "configs/assets.yaml",  # Keep assets_comprehensive.yaml
            "configs/claude_assets_comprehensive.yaml",  # Duplicate
            "configs/after_hours_config.yaml",  # Merged into global.yaml
            "configs/market_specific_strategy.yaml",  # Replaced by profiles
            "configs/sentiment_config.yaml",  # Merged into global.yaml  
            "configs/trading_config.yaml"  # Replaced by profiles
        ]
    }
    
    # Combine all cleanup tasks
    all_cleanup = {**cleanup_plan, **config_cleanup}
    
    total_files = sum(len(files) for files in all_cleanup.values())
    deleted_count = 0
    
    print(f"\n{'🧹 DRY RUN MODE' if dry_run else '🗑️ DELETION MODE'}")
    print("=" * 60)
    print(f"📊 Total files to process: {total_files}")
    
    for category, files in all_cleanup.items():
        print(f"\n📁 {category} ({len(files)} files):")
        
        for file_path in files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / 1024  # KB
                
                if dry_run:
                    print(f"   🔍 WOULD DELETE: {file_path} ({file_size:.1f} KB)")
                else:
                    try:
                        os.remove(file_path)
                        print(f"   ✅ DELETED: {file_path} ({file_size:.1f} KB)")
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ❌ ERROR deleting {file_path}: {e}")
            else:
                print(f"   ⚠️ NOT FOUND: {file_path}")
    
    # Clean up empty directories
    empty_dirs = ["dashboards/", "tests/"]  # Only __init__.py files
    
    print(f"\n📁 Empty Directories to Remove:")
    for dir_path in empty_dirs:
        if os.path.exists(dir_path):
            if dry_run:
                print(f"   🔍 WOULD DELETE: {dir_path}")
            else:
                try:
                    shutil.rmtree(dir_path)
                    print(f"   ✅ DELETED: {dir_path}")
                except Exception as e:
                    print(f"   ❌ ERROR deleting {dir_path}: {e}")
    
    print("\n" + "=" * 60)
    if dry_run:
        print(f"🔍 DRY RUN COMPLETE: Would delete {total_files} files")
        print("   Run with --execute to perform actual deletion")
    else:
        print(f"✅ CLEANUP COMPLETE: Deleted {deleted_count} files")
        print("   Backup created before deletion")
    
    return deleted_count

def validate_core_files():
    """Ensure core production files are still present"""
    critical_files = [
        "scripts/run_conservative.py",
        "scripts/run_aggressive.py", 
        "scripts/run_scalping.py",
        "scripts/run_profile.py",
        "runners/run_multi_market.py",
        "core/professional_strategy_engine.py",
        "core/emergency_risk_manager.py",
        "utils/profile_manager.py",
        "data/db.py",
        "configs/global.yaml",
        "configs/profiles/conservative.yaml",
        "august_8_profile_comparison_backtest.py",
        "README.md",
        "CLAUDE.md"
    ]
    
    print("\n🔍 Validating Core Files:")
    missing_files = []
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ MISSING: {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️ WARNING: {len(missing_files)} critical files missing!")
        return False
    else:
        print(f"\n🎉 All {len(critical_files)} critical files present!")
        return True

def main():
    parser = argparse.ArgumentParser(description="Clean up algo-trader codebase")
    parser.add_argument("--execute", action="store_true", 
                       help="Actually delete files (default: dry run)")
    parser.add_argument("--skip-backup", action="store_true",
                       help="Skip creating backup (not recommended)")
    
    args = parser.parse_args()
    
    print("🧹 Algo-Trader Codebase Cleanup")
    print("=" * 50)
    print("Purpose: Remove redundant files to create clean production codebase")
    print("Focus: Keep multi-profile trading system + essential components")
    
    # Validate we're in the right directory
    if not os.path.exists("CLAUDE.md") or not os.path.exists("scripts/run_conservative.py"):
        print("❌ ERROR: Must run from algo-trader root directory")
        return
    
    # Create backup before cleanup (unless skipped)
    backup_path = None
    if not args.execute:
        print("\n🔍 Running in DRY RUN mode (no files will be deleted)")
    elif not args.skip_backup:
        backup_path = create_backup()
    
    # Execute cleanup
    deleted_count = cleanup_files(dry_run=not args.execute)
    
    # Validate core files remain
    if args.execute:
        core_intact = validate_core_files()
        if not core_intact:
            print(f"\n🚨 CRITICAL: Some core files missing after cleanup!")
            if backup_path:
                print(f"   Restore from backup: {backup_path}")
    
    print(f"\n🎯 CLEANUP SUMMARY:")
    print(f"   Mode: {'EXECUTION' if args.execute else 'DRY RUN'}")
    print(f"   Files Processed: {deleted_count}")
    print(f"   Backup Created: {'Yes' if backup_path else 'No'}")
    print(f"   Core Files: {'✅ Intact' if not args.execute or validate_core_files() else '❌ Issues'}")
    
    if not args.execute:
        print(f"\n🚀 To execute cleanup:")
        print(f"   python3 cleanup_codebase.py --execute")

if __name__ == "__main__":
    main()