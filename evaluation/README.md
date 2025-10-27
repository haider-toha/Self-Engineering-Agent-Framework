# Agent Evaluation Framework

A comprehensive, ML-inspired evaluation framework for the Self-Engineering Agent.

## Quick Start

### Prerequisites

```bash
# Install additional dependencies
pip install matplotlib seaborn psutil
```

### Running Evaluations

```bash
# Full evaluation (all categories)
python evaluation/run_evaluation.py

# Specific categories only
python evaluation/run_evaluation.py --categories functional synthesis retrieval

# With visualizations
python evaluation/run_evaluation.py --visualize

# Custom output directory
python evaluation/run_evaluation.py --output-dir ./my_results
```

### Compare Two Runs

```bash
python evaluation/run_evaluation.py --compare \
    results/evaluation_20250101_120000.json \
    results/evaluation_20250102_120000.json
```

## Framework Structure

```
evaluation/
├── README.md                      # This file
├── EVALUATION_METHODOLOGY.md      # Detailed methodology documentation
├── eval_framework.py              # Core evaluation framework
├── run_evaluation.py              # Main execution script
├── visualization.py               # Visualization and reporting
├── test_dataset_generator.py      # Test dataset generation
├── tests/                         # Test suites
│   ├── __init__.py
│   ├── test_functional.py         # Functional correctness tests
│   ├── test_synthesis.py          # Synthesis quality tests
│   ├── test_retrieval.py          # Tool retrieval tests
│   ├── test_workflow.py           # Multi-tool workflow tests
│   ├── test_learning.py           # Learning & adaptation tests
│   ├── test_robustness.py         # Robustness & edge case tests
│   └── test_performance.py        # Performance & efficiency tests
├── data/                          # Test datasets (generated)
└── results/                       # Evaluation results (generated)
```

## Evaluation Categories

### 1. Functional Correctness
Tests whether the agent produces correct outputs for various tasks.

**Tests**: 8 tests covering arithmetic, strings, math, edge cases  
**Target Score**: ≥ 0.80

### 2. Synthesis Quality
Evaluates the quality of tools created by the agent.

**Tests**: 6 tests for code quality, test coverage, TDD process  
**Target Score**: ≥ 0.70

### 3. Retrieval Performance
Measures how well the agent finds and selects tools.

**Tests**: 6 tests using precision, recall, F1, MRR metrics  
**Target Score**: ≥ 0.75

### 4. Workflow Execution
Tests multi-tool workflow capabilities.

**Tests**: 5 tests for sequential, dependent, and complex workflows  
**Target Score**: ≥ 0.70

### 5. Learning & Adaptation
Measures the agent's learning and improvement over time.

**Tests**: 4 tests for tool reuse, learning curves, patterns  
**Target Score**: ≥ 0.70

### 6. Robustness
Verifies handling of edge cases and errors.

**Tests**: 6 tests for edge cases, invalid inputs, error recovery  
**Target Score**: ≥ 0.75

### 7. Performance
Benchmarks speed and resource efficiency.

**Tests**: 5 tests for response time, memory, throughput  
**Target Score**: ≥ 0.70

## Usage Examples

### Basic Evaluation

```python
from src.orchestrator import AgentOrchestrator
from evaluation.eval_framework import EvaluationFramework

# Initialize
orchestrator = AgentOrchestrator()
framework = EvaluationFramework(orchestrator)

# Run evaluation
results = framework.run_evaluation()

# Print summary
print(f"Pass Rate: {results['summary']['pass_rate']:.1%}")
print(f"Average Score: {results['summary']['average_score']:.3f}")
```

### Category-Specific Evaluation

```python
# Run only functional and performance tests
results = framework.run_evaluation(
    test_suite=['functional', 'performance'],
    save_results=True
)

# Check category scores
functional_score = results['summary']['category_scores']['functional']
performance_score = results['summary']['category_scores']['performance']

print(f"Functional: {functional_score:.3f}")
print(f"Performance: {performance_score:.3f}")
```

### Generate Test Dataset

```python
from evaluation.test_dataset_generator import TestDatasetGenerator

generator = TestDatasetGenerator(seed=42)

dataset = generator.generate_full_dataset(
    num_simple=20,
    num_medium=15,
    num_complex=10,
    include_edge_cases=True
)

generator.save_dataset(dataset, "evaluation/data/my_dataset.json")
```

### Create Visualizations

```python
from evaluation.visualization import EvaluationVisualizer

visualizer = EvaluationVisualizer()

# Generate charts
visualizer.plot_category_scores(
    "results/evaluation_latest.json",
    "charts/category_scores.png"
)

visualizer.plot_test_distribution(
    "results/evaluation_latest.json",
    "charts/distribution.png"
)

# Generate HTML report
visualizer.generate_html_report(
    "results/evaluation_latest.json",
    "reports/report.html"
)
```

## Metrics & Scoring

### ML-Inspired Metrics

The framework uses standard machine learning evaluation metrics:

- **Precision & Recall**: For retrieval quality
- **F1 Score**: Harmonic mean of precision and recall
- **MRR (Mean Reciprocal Rank)**: Ranking quality
- **NDCG**: Normalized discounted cumulative gain
- **Accuracy**: Correctness rate
- **Levenshtein Distance**: Code similarity
- **Cosine Similarity**: Semantic similarity

### Scoring System

- **Test Score**: 0.0 to 1.0 (1.0 = perfect)
- **Category Score**: Average of test scores
- **Overall Score**: Weighted average of categories

**Interpretation**:
- **0.90-1.00**: Excellent
- **0.80-0.90**: Very Good
- **0.70-0.80**: Good (Target)
- **0.60-0.70**: Acceptable
- **< 0.60**: Needs Improvement

### Pass Criteria

- Individual test passes if score ≥ 0.70
- Category passes if average ≥ 0.70
- System passes if overall ≥ 0.70 and no critical failures

## Output Files

### JSON Results
```json
{
  "summary": {
    "total_tests": 44,
    "passed_tests": 38,
    "failed_tests": 6,
    "pass_rate": 0.864,
    "average_score": 0.812,
    "category_scores": { ... },
    "total_execution_time_ms": 145230.5,
    "timestamp": "2025-01-27T14:30:00.000000"
  },
  "detailed_results": [ ... ]
}
```

### Visualizations

1. **Category Scores** - Bar chart showing scores by category
2. **Test Distribution** - Pie/bar charts of pass/fail rates
3. **Performance Metrics** - Execution time and efficiency charts

### HTML Report

Interactive web report with:
- Overall summary metrics
- Category breakdowns
- Detailed test results
- Visual score indicators

## Best Practices

### 1. Regular Evaluation
- Run **weekly** full evaluations
- Run **daily** quick checks (functional + performance)
- Track trends over time

### 2. Baseline Comparison
```python
# Compare against baseline
baseline_score = 0.75
current_score = results['summary']['average_score']

if current_score < baseline_score * 0.95:
    print("⚠ Performance regression detected!")
```

### 3. Regression Testing
- Save all evaluation results
- Compare each run against previous
- Flag score drops > 10%

### 4. Custom Tests

Add your own tests by creating a new test module:

```python
# evaluation/tests/test_custom.py

class CustomTests:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
    
    def run_all(self) -> List[EvaluationResult]:
        results = []
        results.append(self.test_my_feature())
        return results
    
    def test_my_feature(self) -> EvaluationResult:
        # Your test implementation
        pass
```

### 5. CI/CD Integration

```yaml
# .github/workflows/evaluation.yml
name: Agent Evaluation

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run evaluation
        run: python evaluation/run_evaluation.py
      - name: Check pass rate
        run: |
          PASS_RATE=$(jq '.summary.pass_rate' results/evaluation_*.json | tail -1)
          if (( $(echo "$PASS_RATE < 0.70" | bc -l) )); then
            echo "Pass rate below threshold: $PASS_RATE"
            exit 1
          fi
```

## Troubleshooting

### Common Issues

**Issue**: Tests fail to initialize orchestrator  
**Solution**: Check environment variables, Supabase connection, Docker status

**Issue**: Synthesis tests fail  
**Solution**: Verify OpenAI API key, check Docker sandbox is running

**Issue**: Memory errors during evaluation  
**Solution**: Run categories separately, increase system memory

**Issue**: Slow evaluation times  
**Solution**: Reduce test count, run on faster hardware, check network latency

### Debug Mode

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run single test
from evaluation.tests.test_functional import FunctionalTests
tests = FunctionalTests(orchestrator)
result = tests.test_percentage_calculation()
print(result)
```

## Contributing

To add new tests or improve the framework:

1. Create new test methods following existing patterns
2. Use `EvaluationResult` for consistency
3. Document expected behavior and scoring
4. Add to appropriate test category
5. Update this README

## Documentation

- **[EVALUATION_METHODOLOGY.md](./EVALUATION_METHODOLOGY.md)** - Comprehensive methodology guide
- **[Main README](../README.md)** - Project overview
- **[API Documentation](../docs/API.md)** - API reference

## License

Same as parent project (see [LICENSE](../LICENSE))

## Support

For issues or questions:
1. Check [EVALUATION_METHODOLOGY.md](./EVALUATION_METHODOLOGY.md)
2. Review existing test implementations
3. Open an issue on GitHub

---

**Version**: 1.0.0  
**Last Updated**: October 27, 2025

