"""
Evaluation test modules for Self-Engineering Agent
"""

from evaluation.tests.test_functional import FunctionalTests
from evaluation.tests.test_synthesis import SynthesisTests
from evaluation.tests.test_retrieval import RetrievalTests
from evaluation.tests.test_workflow import WorkflowTests
from evaluation.tests.test_learning import LearningTests
from evaluation.tests.test_robustness import RobustnessTests
from evaluation.tests.test_performance import PerformanceTests

__all__ = [
    'FunctionalTests',
    'SynthesisTests',
    'RetrievalTests',
    'WorkflowTests',
    'LearningTests',
    'RobustnessTests',
    'PerformanceTests'
]

