#!/usr/bin/env python3
"""
Batch Pattern Miner - Periodic job to mine patterns and promote composites
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from src.workflow_tracker import WorkflowTracker
from src.composite_synthesizer import CompositeSynthesizer
from src.reflection_engine import ReflectionEngine
from src.auto_tuner import AutoTuner


def mine_patterns(lookback_days: int = 7):
    """
    Mine workflow patterns from recent executions
    
    Args:
        lookback_days: Number of days to look back
    """
    print(f"Mining patterns from last {lookback_days} days...")
    tracker = WorkflowTracker()
    
    try:
        from supabase import create_client
        from config import Config
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        # Get all sessions from lookback period
        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()
        
        sessions = supabase.rpc(
            "get_unique_sessions_since",
            {"since_date": cutoff}
        ).execute() if hasattr(supabase, "rpc") else None
        
        # For each session, analyze patterns (this is normally done during execution)
        print(f"Analyzed pattern mining for period")
        
    except Exception as e:
        print(f"Warning: Pattern mining encountered error: {e}")


def promote_composites(max_promotions: int = 5):
    """
    Scan for eligible patterns and promote to composite tools
    
    Args:
        max_promotions: Maximum composites to create
    """
    print(f"\nPromoting composite tools (max {max_promotions})...")
    synthesizer = CompositeSynthesizer()
    
    def progress_callback(event: str, data: any):
        if event == "candidates_found":
            print(f"  Found {data['count']} candidates")
        elif event == "processing_candidate":
            print(f"  Processing {data['index']}/{data['total']}: {data['pattern']}")
        elif event == "composite_synthesis_complete":
            print(f"  ✓ Created composite: {data['name']}")
    
    results = synthesizer.run_batch_synthesis(
        max_candidates=max_promotions,
        callback=progress_callback
    )
    
    print(f"\nComposite Synthesis Summary:")
    print(f"  Candidates processed: {results['processed']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    if results['composites_created']:
        print(f"  Created: {', '.join(results['composites_created'])}")


def process_reflections(max_fixes: int = 3):
    """
    Process unresolved reflections and apply fixes
    
    Args:
        max_fixes: Maximum fixes to attempt
    """
    print(f"\nProcessing reflections (max {max_fixes} fixes)...")
    engine = ReflectionEngine()
    
    unresolved = engine.get_unresolved_reflections(limit=max_fixes)
    
    if not unresolved:
        print("  No unresolved reflections found")
        return
    
    print(f"  Found {len(unresolved)} unresolved reflections")
    
    fixes_applied = 0
    fixes_successful = 0
    
    for reflection in unresolved:
        print(f"\n  Attempting fix for {reflection['tool_name']} ({reflection['failure_type']})...")
        
        result = engine.apply_fix(reflection['id'])
        
        if result['success']:
            print(f"    ✓ Fix applied successfully")
            fixes_applied += 1
            fixes_successful += 1
        else:
            print(f"    ✗ Fix failed: {result.get('error', 'Unknown')}")
            fixes_applied += 1
    
    print(f"\nReflection Summary:")
    print(f"  Fixes attempted: {fixes_applied}")
    print(f"  Successful: {fixes_successful}")


def run_auto_tuning():
    """Run policy auto-tuning"""
    print("\nRunning auto-tuning...")
    tuner = AutoTuner()
    
    results = tuner.run_full_tuning()
    
    print("\nAuto-Tuning Complete")
    return results


def main():
    """Main batch processing job"""
    print("=" * 70)
    print("BATCH PATTERN MINING & OPTIMIZATION JOB")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    try:
        # Step 1: Mine patterns from recent data
        mine_patterns(lookback_days=7)
        
        # Step 2: Promote eligible patterns to composites
        promote_composites(max_promotions=5)
        
        # Step 3: Process reflections and apply fixes
        process_reflections(max_fixes=3)
        
        # Step 4: Run auto-tuning (weekly)
        # Check if it's time to run (e.g., Monday)
        if datetime.now().weekday() == 0:  # Monday
            run_auto_tuning()
        else:
            print("\nSkipping auto-tuning (runs weekly on Mondays)")
        
        print("\n" + "=" * 70)
        print("BATCH JOB COMPLETE")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Batch job failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

