#!/usr/bin/env python3
"""
📊 Profile Performance Analyzer

Analyzes and compares performance across different trading profiles
for weekly A/B testing and optimization decisions.

Author: Multi-Profile Trading System
"""

import os
import sys
import json
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.db import trades_collection
from utils.profile_manager import TradingProfileManager

class ProfileAnalyzer:
    """Analyze and compare trading profile performance"""
    
    def __init__(self):
        """Initialize profile analyzer"""
        self.profile_manager = TradingProfileManager()
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
    def analyze_session_reports(self, days_back: int = 7) -> Dict:
        """Analyze session reports from the last N days"""
        
        # Find all session reports
        pattern = str(self.reports_dir / "session_report_*.json")
        report_files = glob.glob(pattern)
        
        # Filter by date
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_reports = []
        
        for report_file in report_files:
            try:
                with open(report_file, 'r') as f:
                    report = json.load(f)
                
                # Parse date from filename or report
                report_date = datetime.fromisoformat(report['session_info']['start_time'])
                
                if report_date >= cutoff_date:
                    recent_reports.append({
                        'file': report_file,
                        'data': report,
                        'date': report_date
                    })
                    
            except Exception as e:
                print(f"⚠️ Error reading report {report_file}: {e}")
        
        # Group by profile
        profile_data = {
            'conservative': [],
            'aggressive': [],
            'scalping': []
        }
        
        for report in recent_reports:
            profile = report['data']['profile']
            if profile in profile_data:
                profile_data[profile].append(report)
        
        # Analyze each profile
        analysis = {}
        for profile_name, reports in profile_data.items():
            if reports:
                analysis[profile_name] = self._analyze_profile_reports(reports)
            else:
                analysis[profile_name] = {'error': 'No reports found'}
        
        return {
            'analysis_period': f"Last {days_back} days",
            'total_reports': len(recent_reports),
            'profiles': analysis,
            'generated_at': datetime.now().isoformat()
        }
    
    def _analyze_profile_reports(self, reports: List[Dict]) -> Dict:
        """Analyze reports for a specific profile"""
        
        if not reports:
            return {'error': 'No reports to analyze'}
        
        # Extract metrics
        sessions = []
        total_trades = 0
        total_pnl = 0
        total_duration = timedelta()
        balance_changes = []
        win_rates = []
        
        for report in reports:
            perf = report['data']['performance']
            session_info = report['data']['session_info']
            
            sessions.append({
                'date': report['date'],
                'trades': perf['total_trades'],
                'pnl': perf['total_pnl'],
                'balance_change': perf['balance_change'],
                'win_rate': perf['win_rate'],
                'duration': session_info.get('duration', '0:00:00')
            })
            
            total_trades += perf['total_trades']
            total_pnl += perf['total_pnl']
            balance_changes.append(perf['balance_change'])
            win_rates.append(perf['win_rate'])
        
        # Calculate aggregated metrics
        avg_win_rate = np.mean(win_rates) if win_rates else 0
        avg_balance_change = np.mean(balance_changes) if balance_changes else 0
        total_balance_change = sum(balance_changes)
        
        # Calculate consistency metrics
        win_rate_std = np.std(win_rates) if len(win_rates) > 1 else 0
        balance_change_std = np.std(balance_changes) if len(balance_changes) > 1 else 0
        
        # Determine profitability
        profitable_sessions = len([bc for bc in balance_changes if bc > 0])
        profitability_rate = (profitable_sessions / len(balance_changes)) * 100 if balance_changes else 0
        
        return {
            'sessions_count': len(sessions),
            'total_trades': total_trades,
            'avg_trades_per_session': total_trades / len(sessions) if sessions else 0,
            'total_pnl': total_pnl,
            'total_balance_change': total_balance_change,
            'avg_balance_change_per_session': avg_balance_change,
            'avg_win_rate': avg_win_rate,
            'win_rate_consistency': win_rate_std,
            'balance_consistency': balance_change_std,
            'profitability_rate': profitability_rate,
            'best_session': max(balance_changes) if balance_changes else 0,
            'worst_session': min(balance_changes) if balance_changes else 0,
            'sessions': sessions[-5:]  # Last 5 sessions
        }
    
    def generate_weekly_comparison(self, week_offset: int = 0) -> Dict:
        """Generate weekly comparison report"""
        
        # Calculate week boundaries
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday() + (week_offset * 7))
        week_end = week_start + timedelta(days=7)
        
        print(f"📅 Analyzing week: {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}")
        
        # Get trades from database for this week
        week_trades = list(trades_collection.find({
            'timestamp': {
                '$gte': week_start,
                '$lt': week_end
            }
        }))
        
        # Get session reports for this week
        session_analysis = self.analyze_session_reports(days_back=7)
        
        # Calculate overall week metrics
        week_metrics = self._calculate_week_metrics(week_trades)
        
        return {
            'week_info': {
                'week_number': week_start.isocalendar()[1],
                'year': week_start.year,
                'start_date': week_start.isoformat(),
                'end_date': week_end.isoformat(),
                'week_offset': week_offset
            },
            'overall_metrics': week_metrics,
            'profile_analysis': session_analysis['profiles'],
            'recommendation': self._generate_recommendation(session_analysis['profiles']),
            'generated_at': datetime.now().isoformat()
        }
    
    def _calculate_week_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate overall week metrics from trades"""
        
        if not trades:
            return {
                'total_trades': 0,
                'total_pnl': 0,
                'win_rate': 0,
                'avg_trade_pnl': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        # Extract P&L values
        pnl_values = [t.get('profit_loss', 0) for t in trades if t.get('profit_loss') is not None]
        
        if not pnl_values:
            return {
                'total_trades': len(trades),
                'total_pnl': 0,
                'win_rate': 0,
                'avg_trade_pnl': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        # Calculate metrics
        winning_trades = [pnl for pnl in pnl_values if pnl > 0]
        win_rate = (len(winning_trades) / len(pnl_values)) * 100
        
        return {
            'total_trades': len(trades),
            'total_pnl': sum(pnl_values),
            'win_rate': win_rate,
            'avg_trade_pnl': np.mean(pnl_values),
            'best_trade': max(pnl_values),
            'worst_trade': min(pnl_values),
            'winning_trades': len(winning_trades),
            'losing_trades': len(pnl_values) - len(winning_trades)
        }
    
    def _generate_recommendation(self, profile_analysis: Dict) -> Dict:
        """Generate recommendation based on profile performance"""
        
        profiles_with_data = {k: v for k, v in profile_analysis.items() if 'error' not in v}
        
        if not profiles_with_data:
            return {
                'recommended_profile': None,
                'reason': 'No profile data available',
                'confidence': 'LOW'
            }
        
        # Score each profile
        scores = {}
        for profile_name, data in profiles_with_data.items():
            score = 0
            
            # Profitability (40% weight)
            if data.get('total_balance_change', 0) > 0:
                score += 40
            
            # Win rate (30% weight)
            win_rate = data.get('avg_win_rate', 0)
            if win_rate > 60:
                score += 30
            elif win_rate > 50:
                score += 20
            elif win_rate > 40:
                score += 10
            
            # Consistency (20% weight)
            consistency = data.get('balance_consistency', float('inf'))
            if consistency < 50:  # Low volatility is good
                score += 20
            elif consistency < 100:
                score += 10
            
            # Profitability rate (10% weight)
            prof_rate = data.get('profitability_rate', 0)
            if prof_rate > 70:
                score += 10
            elif prof_rate > 50:
                score += 5
            
            scores[profile_name] = score
        
        # Find best profile
        if scores:
            best_profile = max(scores, key=scores.get)
            best_score = scores[best_profile]
            
            # Determine confidence
            if best_score >= 80:
                confidence = 'HIGH'
            elif best_score >= 60:
                confidence = 'MEDIUM'
            else:
                confidence = 'LOW'
            
            # Generate reason
            best_data = profiles_with_data[best_profile]
            reason_parts = []
            
            if best_data.get('total_balance_change', 0) > 0:
                reason_parts.append(f"profitable (£{best_data['total_balance_change']:.2f})")
            
            if best_data.get('avg_win_rate', 0) > 50:
                reason_parts.append(f"{best_data['avg_win_rate']:.1f}% win rate")
            
            if best_data.get('profitability_rate', 0) > 50:
                reason_parts.append(f"{best_data['profitability_rate']:.0f}% session success")
            
            reason = f"{best_profile.title()} profile: " + ", ".join(reason_parts)
            
            return {
                'recommended_profile': best_profile,
                'reason': reason,
                'confidence': confidence,
                'score': best_score,
                'all_scores': scores
            }
        
        return {
            'recommended_profile': 'conservative',
            'reason': 'Default to conservative due to insufficient data',
            'confidence': 'LOW'
        }
    
    def compare_profiles_side_by_side(self, days_back: int = 7) -> str:
        """Generate side-by-side profile comparison report"""
        
        analysis = self.analyze_session_reports(days_back)
        
        report = f"""
📊 TRADING PROFILE COMPARISON REPORT
{'='*60}
Analysis Period: {analysis['analysis_period']}
Total Reports: {analysis['total_reports']}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        # Profile comparison table
        profiles = analysis['profiles']
        
        if any('error' not in v for v in profiles.values()):
            report += f"""
{'Profile':<15} {'Sessions':<10} {'Trades':<8} {'Win Rate':<10} {'Total P&L':<12} {'Profit Rate':<12}
{'-'*70}
"""
            
            for profile_name in ['conservative', 'aggressive', 'scalping']:
                data = profiles.get(profile_name, {})
                
                if 'error' in data:
                    sessions = "N/A"
                    trades = "N/A"
                    win_rate = "N/A"
                    pnl = "N/A"
                    profit_rate = "N/A"
                else:
                    sessions = str(data.get('sessions_count', 0))
                    trades = str(data.get('total_trades', 0))
                    win_rate = f"{data.get('avg_win_rate', 0):.1f}%"
                    pnl = f"£{data.get('total_balance_change', 0):.2f}"
                    profit_rate = f"{data.get('profitability_rate', 0):.0f}%"
                
                report += f"{profile_name.title():<15} {sessions:<10} {trades:<8} {win_rate:<10} {pnl:<12} {profit_rate:<12}\n"
        
        # Detailed analysis for each profile
        for profile_name, data in profiles.items():
            if 'error' not in data:
                report += f"""

🔍 {profile_name.upper()} PROFILE ANALYSIS:
   Sessions Analyzed: {data.get('sessions_count', 0)}
   Total Trades: {data.get('total_trades', 0)}
   Average Win Rate: {data.get('avg_win_rate', 0):.1f}%
   Total Balance Change: £{data.get('total_balance_change', 0):.2f}
   Average per Session: £{data.get('avg_balance_change_per_session', 0):.2f}
   Profitable Sessions: {data.get('profitability_rate', 0):.0f}%
   Best Session: £{data.get('best_session', 0):.2f}
   Worst Session: £{data.get('worst_session', 0):.2f}
   Consistency Score: {100 - min(100, data.get('balance_consistency', 0)):.0f}/100
"""
        
        # Add recommendation
        weekly_comp = self.generate_weekly_comparison()
        recommendation = weekly_comp.get('recommendation', {})
        
        if recommendation.get('recommended_profile'):
            report += f"""

💡 RECOMMENDATION:
   Recommended Profile: {recommendation['recommended_profile'].upper()}
   Confidence: {recommendation.get('confidence', 'LOW')}
   Reason: {recommendation.get('reason', 'N/A')}

"""
        
        report += f"""
{'='*60}
🔄 To switch to recommended profile:
   python3 scripts/run_{recommendation.get('recommended_profile', 'conservative')}.py --duration 7d

📊 To run all profiles for testing:
   python3 scripts/run_conservative.py --duration 1d --paper
   python3 scripts/run_aggressive.py --duration 1d --paper  
   python3 scripts/run_scalping.py --duration 1d --paper
"""
        
        return report

def main():
    """Main entry point for profile analysis"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze trading profile performance")
    parser.add_argument("--days", "-d", type=int, default=7,
                       help="Number of days to analyze (default: 7)")
    parser.add_argument("--week", "-w", type=int, default=0,
                       help="Week offset (0=current week, 1=last week)")
    parser.add_argument("--save", "-s", action="store_true",
                       help="Save report to file")
    
    args = parser.parse_args()
    
    analyzer = ProfileAnalyzer()
    
    if args.week > 0:
        # Weekly comparison
        print(f"📅 Generating weekly comparison report (week offset: {args.week})")
        comparison = analyzer.generate_weekly_comparison(args.week)
        
        print(f"\n📊 WEEKLY COMPARISON - Week {comparison['week_info']['week_number']}")
        print(f"Period: {comparison['week_info']['start_date'][:10]} to {comparison['week_info']['end_date'][:10]}")
        
        recommendation = comparison.get('recommendation', {})
        if recommendation.get('recommended_profile'):
            print(f"\n💡 RECOMMENDATION: {recommendation['recommended_profile'].upper()}")
            print(f"Confidence: {recommendation.get('confidence')}")
            print(f"Reason: {recommendation.get('reason')}")
    
    else:
        # Session analysis  
        print(f"📊 Generating profile comparison report ({args.days} days)")
        report = analyzer.compare_profiles_side_by_side(args.days)
        print(report)
        
        if args.save:
            filename = f"reports/profile_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w') as f:
                f.write(report)
            print(f"\n📄 Report saved to: {filename}")

if __name__ == "__main__":
    main()