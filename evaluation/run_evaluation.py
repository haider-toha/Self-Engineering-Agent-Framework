"""
Evaluation Runner Script

Main script to run comprehensive agent evaluation.
"""

import sys
import os
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.orchestrator import AgentOrchestrator
from evaluation.eval_framework import EvaluationFramework
from evaluation.visualization import EvaluationVisualizer


def main():
    """Main evaluation runner"""
    parser = argparse.ArgumentParser(description='Run comprehensive agent evaluation')
    
    parser.add_argument(
        '--categories',
        nargs='+',
        choices=['functional', 'synthesis', 'retrieval', 'workflow', 'learning', 'robustness', 'performance'],
        help='Specific test categories to run (default: all)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./evaluation/results',
        help='Output directory for results'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save results to disk'
    )
    
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Generate visualization charts'
    )
    
    parser.add_argument(
        '--compare',
        type=str,
        nargs=2,
        metavar=('FILE1', 'FILE2'),
        help='Compare two evaluation result files'
    )
    
    args = parser.parse_args()
    
    # If comparing results
    if args.compare:
        print("Comparing evaluation results...")
        framework = EvaluationFramework()
        comparison = framework.compare_runs(args.compare[0], args.compare[1])
        
        print("\n" + "=" * 80)
        print("COMPARISON RESULTS")
        print("=" * 80)
        print(f"\nRun 1: {comparison['run1']['timestamp']}")
        print(f"  Pass Rate: {comparison['run1']['pass_rate']:.1%}")
        print(f"  Average Score: {comparison['run1']['average_score']:.3f}")
        
        print(f"\nRun 2: {comparison['run2']['timestamp']}")
        print(f"  Pass Rate: {comparison['run2']['pass_rate']:.1%}")
        print(f"  Average Score: {comparison['run2']['average_score']:.3f}")
        
        print("\nImprovements:")
        print(f"  Pass Rate Delta: {comparison['improvements']['pass_rate_delta']:+.1%}")
        print(f"  Score Delta: {comparison['improvements']['score_delta']:+.3f}")
        
        print("\nCategory Comparison:")
        for category, scores in comparison['category_comparison'].items():
            delta = scores['delta']
            symbol = "↑" if delta > 0 else "↓" if delta < 0 else "="
            print(f"  {category.capitalize()}: {scores['run1']:.3f} -> {scores['run2']:.3f} ({symbol} {abs(delta):.3f})")
        
        return
    
    print("=" * 80)
    print("SELF-ENGINEERING AGENT - COMPREHENSIVE EVALUATION")
    print("=" * 80)
    print(f"\nStarting evaluation at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize the orchestrator
    print("\nInitializing agent orchestrator...")
    try:
        orchestrator = AgentOrchestrator()
        tool_count = orchestrator.get_tool_count()
        print(f"✓ Orchestrator initialized with {tool_count} existing tools")
    except Exception as e:
        print(f"✗ Failed to initialize orchestrator: {str(e)}")
        print("\nPlease ensure:")
        print("  1. Environment variables are set correctly (.env file)")
        print("  2. Supabase is configured and accessible")
        print("  3. Docker is running for sandbox tests")
        return
    
    # Initialize evaluation framework
    framework = EvaluationFramework(
        orchestrator=orchestrator,
        results_dir=args.output_dir
    )
    
    # Run evaluation
    print("\nStarting evaluation suite...")
    print("This may take several minutes depending on the categories tested.\n")
    
    results = framework.run_evaluation(
        test_suite=args.categories,
        save_results=not args.no_save
    )
    
    # Generate visualizations if requested
    if args.visualize:
        print("\nGenerating visualizations...")
        try:
            visualizer = EvaluationVisualizer()
            
            # Get the latest results file
            import glob
            result_files = glob.glob(f"{args.output_dir}/evaluation_*.json")
            if result_files:
                latest_file = max(result_files, key=os.path.getctime)
                
                # Generate charts
                viz_dir = f"{args.output_dir}/visualizations"
                os.makedirs(viz_dir, exist_ok=True)
                
                visualizer.plot_category_scores(latest_file, f"{viz_dir}/category_scores.png")
                visualizer.plot_test_distribution(latest_file, f"{viz_dir}/test_distribution.png")
                visualizer.plot_performance_metrics(latest_file, f"{viz_dir}/performance.png")
                
                print(f"✓ Visualizations saved to {viz_dir}")
        except Exception as e:
            print(f"✗ Failed to generate visualizations: {str(e)}")
    
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

