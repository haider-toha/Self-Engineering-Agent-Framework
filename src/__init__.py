"""
Self-Engineering Agent Framework
"""

__version__ = "1.0.0"
__author__ = "Self-Engineering Agent Framework"

from src.orchestrator import AgentOrchestrator
from src.capability_registry import CapabilityRegistry
from src.synthesis_engine import CapabilitySynthesisEngine
from src.executor import ToolExecutor
from src.response_synthesizer import ResponseSynthesizer
from src.sandbox import SecureSandbox
from src.llm_client import LLMClient

__all__ = [
    'AgentOrchestrator',
    'CapabilityRegistry',
    'CapabilitySynthesisEngine',
    'ToolExecutor',
    'ResponseSynthesizer',
    'SecureSandbox',
    'LLMClient',
]

