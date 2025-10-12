"""
Installation Test - Verify all components are working
"""

import sys
import os
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 70)
print("Self-Engineering Agent Framework - Installation Test")
print("=" * 70)
print()

# Test 1: Python Version
print("1. Testing Python version...")
if sys.version_info >= (3, 10):
    print(f"   ✓ Python {sys.version.split()[0]} (OK)")
else:
    print(f"   ✗ Python {sys.version.split()[0]} (Requires 3.10+)")
    sys.exit(1)

# Test 2: Import core modules
print("\n2. Testing core module imports...")
try:
    import config
    print("   ✓ config")
    from src.llm_client import LLMClient
    print("   ✓ src.llm_client")
    from src.capability_registry import CapabilityRegistry
    print("   ✓ src.capability_registry")
    from src.sandbox import SecureSandbox
    print("   ✓ src.sandbox")
    from src.synthesis_engine import CapabilitySynthesisEngine
    print("   ✓ src.synthesis_engine")
    from src.executor import ToolExecutor
    print("   ✓ src.executor")
    from src.response_synthesizer import ResponseSynthesizer
    print("   ✓ src.response_synthesizer")
    from src.orchestrator import AgentOrchestrator
    print("   ✓ src.orchestrator")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 3: Check dependencies
print("\n3. Testing dependencies...")
try:
    import openai
    print("   ✓ openai")
    import chromadb
    print("   ✓ chromadb")
    import flask
    print("   ✓ flask")
    import flask_socketio
    print("   ✓ flask_socketio")
    import docker
    print("   ✓ docker")
    import pytest
    print("   ✓ pytest")
    import dotenv
    print("   ✓ python-dotenv")
except ImportError as e:
    print(f"   ✗ Dependency missing: {e}")
    print("   Run: pip install -r requirements.txt")
    sys.exit(1)

# Test 4: Check environment configuration
print("\n4. Testing environment configuration...")
if os.path.exists(".env"):
    print("   ✓ .env file exists")
    try:
        from config import Config
        if Config.OPENAI_API_KEY and Config.OPENAI_API_KEY != "your_api_key_here":
            print("   ✓ OPENAI_API_KEY is set")
        else:
            print("   ⚠ OPENAI_API_KEY not configured (set it in .env)")
    except Exception as e:
        print(f"   ⚠ Configuration warning: {e}")
else:
    print("   ⚠ .env file not found (copy .env.example to .env)")

# Test 5: Check Docker
print("\n5. Testing Docker connection...")
try:
    import docker
    client = docker.from_env()
    client.ping()
    print("   ✓ Docker is running")
except Exception as e:
    print(f"   ⚠ Docker not accessible: {e}")
    print("   Make sure Docker Desktop is running")

# Test 6: Check directory structure
print("\n6. Testing directory structure...")
required_dirs = ["src", "web", "web/templates", "web/static", "docker", "tools"]
for dir_path in required_dirs:
    if os.path.exists(dir_path):
        print(f"   ✓ {dir_path}/")
    else:
        print(f"   ✗ {dir_path}/ missing")

# Test 7: Check required files
print("\n7. Testing required files...")
required_files = [
    "config.py",
    "requirements.txt",
    "README.md",
    "docker/sandbox.dockerfile",
    "web/app.py",
    "web/templates/index.html",
    "web/static/style.css",
    "web/static/script.js",
]
for file_path in required_files:
    if os.path.exists(file_path):
        print(f"   ✓ {file_path}")
    else:
        print(f"   ✗ {file_path} missing")

# Test 8: Test component initialization
print("\n8. Testing component initialization...")
try:
    registry = CapabilityRegistry()
    print(f"   ✓ CapabilityRegistry ({registry.count_tools()} tools)")
except Exception as e:
    print(f"   ✗ CapabilityRegistry failed: {e}")

try:
    sandbox = SecureSandbox()
    print("   ✓ SecureSandbox")
except Exception as e:
    print(f"   ⚠ SecureSandbox: {e}")

try:
    orchestrator = AgentOrchestrator()
    print(f"   ✓ AgentOrchestrator ({orchestrator.get_tool_count()} tools)")
except Exception as e:
    print(f"   ✗ AgentOrchestrator failed: {e}")

# Summary
print("\n" + "=" * 70)
print("Installation Test Complete!")
print("=" * 70)
print("\nNext steps:")
print("  1. If any tests failed, address the issues above")
print("  2. Make sure Docker Desktop is running")
print("  3. Configure your .env file with OPENAI_API_KEY")
print("  4. Run: python setup.py (to build Docker image and seed tools)")
print("  5. Start the agent: python web/app.py")
print("=" * 70)

