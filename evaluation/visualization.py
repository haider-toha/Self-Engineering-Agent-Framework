"""
Evaluation Visualization

Creates charts and graphs for evaluation results.
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from typing import Dict, Any, List


class EvaluationVisualizer:
    """
    Creates visualizations for evaluation results.
    Generates charts, graphs, and reports.
    """
    
    def __init__(self):
        """Initialize the visualizer"""
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
    
    def load_results(self, filepath: str) -> Dict[str, Any]:
        """Load evaluation results from file"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def plot_category_scores(self, results_file: str, output_file: str):
        """
        Plot scores by category as a bar chart
        
        Args:
            results_file: Path to results JSON file
            output_file: Path to save the plot
        """
        results = self.load_results(results_file)
        summary = results['summary']
        
        # Extract category scores
        categories = []
        scores = []
        
        for category, score in summary['category_scores'].items():
            if score is not None:
                categories.append(category.replace('_', ' ').title())
                scores.append(score)
        
        # Create bar plot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars = ax.bar(categories, scores, color='steelblue', alpha=0.8)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f'{height:.3f}',
                ha='center',
                va='bottom'
            )
        
        ax.set_ylabel('Score', fontsize=12, fontweight='bold')
        ax.set_xlabel('Category', fontsize=12, fontweight='bold')
        ax.set_title('Evaluation Scores by Category', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 1.1)
        ax.axhline(y=0.7, color='green', linestyle='--', alpha=0.5, label='Good (0.7)')
        ax.axhline(y=0.5, color='orange', linestyle='--', alpha=0.5, label='Acceptable (0.5)')
        ax.legend()
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_test_distribution(self, results_file: str, output_file: str):
        """
        Plot test pass/fail distribution
        
        Args:
            results_file: Path to results JSON file
            output_file: Path to save the plot
        """
        results = self.load_results(results_file)
        summary = results['summary']
        
        # Create pie chart
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Overall pass/fail
        sizes = [summary['passed_tests'], summary['failed_tests']]
        labels = [f"Passed\n({summary['passed_tests']})", f"Failed\n({summary['failed_tests']})"]
        colors = ['#2ecc71', '#e74c3c']
        explode = (0.05, 0)
        
        ax1.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=90)
        ax1.set_title('Overall Test Results', fontsize=14, fontweight='bold')
        
        # Category-wise test counts
        category_counts = {}
        for test in results['detailed_results']:
            category = test['category']
            if category not in category_counts:
                category_counts[category] = {'passed': 0, 'failed': 0}
            
            if test['passed']:
                category_counts[category]['passed'] += 1
            else:
                category_counts[category]['failed'] += 1
        
        categories = list(category_counts.keys())
        passed_counts = [category_counts[c]['passed'] for c in categories]
        failed_counts = [category_counts[c]['failed'] for c in categories]
        
        x = np.arange(len(categories))
        width = 0.35
        
        ax2.bar(x - width/2, passed_counts, width, label='Passed', color='#2ecc71', alpha=0.8)
        ax2.bar(x + width/2, failed_counts, width, label='Failed', color='#e74c3c', alpha=0.8)
        
        ax2.set_ylabel('Test Count', fontweight='bold')
        ax2.set_xlabel('Category', fontweight='bold')
        ax2.set_title('Test Distribution by Category', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels([c.replace('_', ' ').title() for c in categories], rotation=45, ha='right')
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_performance_metrics(self, results_file: str, output_file: str):
        """
        Plot performance metrics
        
        Args:
            results_file: Path to results JSON file
            output_file: Path to save the plot
        """
        results = self.load_results(results_file)
        
        # Extract performance test results
        perf_tests = [
            test for test in results['detailed_results']
            if test['category'] == 'performance'
        ]
        
        if not perf_tests:
            print("No performance tests found")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. Execution times
        test_names = [test['test_name'] for test in perf_tests]
        execution_times = [test['execution_time_ms'] for test in perf_tests]
        
        ax1.barh(test_names, execution_times, color='steelblue', alpha=0.8)
        ax1.set_xlabel('Execution Time (ms)', fontweight='bold')
        ax1.set_title('Test Execution Times', fontsize=12, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        
        # 2. Scores distribution
        scores = [test['score'] for test in perf_tests]
        ax2.hist(scores, bins=10, color='green', alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Score', fontweight='bold')
        ax2.set_ylabel('Frequency', fontweight='bold')
        ax2.set_title('Performance Scores Distribution', fontsize=12, fontweight='bold')
        ax2.axvline(x=np.mean(scores), color='red', linestyle='--', label=f'Mean: {np.mean(scores):.3f}')
        ax2.legend()
        
        # 3. Pass/Fail
        passed = sum(1 for test in perf_tests if test['passed'])
        failed = len(perf_tests) - passed
        
        sizes = [passed, failed]
        labels = [f'Passed ({passed})', f'Failed ({failed})']
        colors = ['#2ecc71', '#e74c3c']
        
        ax3.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                shadow=True, startangle=90)
        ax3.set_title('Performance Tests Pass/Fail', fontsize=12, fontweight='bold')
        
        # 4. Score vs Execution Time scatter
        ax4.scatter(execution_times, scores, c=scores, cmap='RdYlGn', 
                   s=100, alpha=0.6, edgecolors='black')
        ax4.set_xlabel('Execution Time (ms)', fontweight='bold')
        ax4.set_ylabel('Score', fontweight='bold')
        ax4.set_title('Score vs Execution Time', fontsize=12, fontweight='bold')
        ax4.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_html_report(self, results_file: str, output_file: str):
        """
        Generate an HTML report
        
        Args:
            results_file: Path to results JSON file
            output_file: Path to save the HTML report
        """
        results = self.load_results(results_file)
        summary = results['summary']
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Evaluation Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px;
        }}
        .metric-value {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
        }}
        .category-scores {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .category-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .score-bar {{
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
        }}
        .score-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
        .test-list {{
            margin-top: 20px;
        }}
        .test-item {{
            background: white;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .pass {{ color: #2ecc71; font-weight: bold; }}
        .fail {{ color: #e74c3c; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Self-Engineering Agent Evaluation Report</h1>
        <p>Timestamp: {summary['timestamp']}</p>
    </div>
    
    <div class="summary-card">
        <h2>Overall Summary</h2>
        <div class="metric">
            <div class="metric-value">{summary['total_tests']}</div>
            <div class="metric-label">Total Tests</div>
        </div>
        <div class="metric">
            <div class="metric-value" style="color: #2ecc71;">{summary['passed_tests']}</div>
            <div class="metric-label">Passed</div>
        </div>
        <div class="metric">
            <div class="metric-value" style="color: #e74c3c;">{summary['failed_tests']}</div>
            <div class="metric-label">Failed</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary['pass_rate']:.1%}</div>
            <div class="metric-label">Pass Rate</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary['average_score']:.3f}</div>
            <div class="metric-label">Average Score</div>
        </div>
    </div>
    
    <div class="summary-card">
        <h2>Category Scores</h2>
        <div class="category-scores">
"""
        
        for category, score in summary['category_scores'].items():
            if score is not None:
                fill_width = score * 100
                html += f"""
            <div class="category-card">
                <h3>{category.replace('_', ' ').title()}</h3>
                <div class="score-bar">
                    <div class="score-fill" style="width: {fill_width}%">
                        {score:.3f}
                    </div>
                </div>
            </div>
"""
        
        html += """
        </div>
    </div>
    
    <div class="summary-card">
        <h2>Detailed Test Results</h2>
        <div class="test-list">
"""
        
        for test in results['detailed_results']:
            status_class = 'pass' if test['passed'] else 'fail'
            status_text = ' PASSED' if test['passed'] else '✗ FAILED'
            
            html += f"""
            <div class="test-item">
                <div>
                    <strong>{test['test_name']}</strong> ({test['category']})
                    <br>
                    <small>Execution Time: {test['execution_time_ms']:.2f}ms | Score: {test['score']:.3f}</small>
                </div>
                <div class="{status_class}">{status_text}</div>
            </div>
"""
        
        html += """
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html)
        
        print(f"HTML report saved to {output_file}")


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python visualization.py <results_file>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    visualizer = EvaluationVisualizer()
    
    print("Generating visualizations...")
    visualizer.plot_category_scores(results_file, "category_scores.png")
    visualizer.plot_test_distribution(results_file, "test_distribution.png")
    visualizer.plot_performance_metrics(results_file, "performance.png")
    visualizer.generate_html_report(results_file, "report.html")
    print("Done!")

