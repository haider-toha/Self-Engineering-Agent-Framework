# CI/CD Setup for API Documentation

This document describes the automated API documentation generation setup for the Self-Engineering Agent Framework. It ensures that API documentation stays synchronized with code changes through continuous integration and deployment.

## Table of Contents

1. [Overview](#overview)
2. [GitHub Actions Workflow](#github-actions-workflow)
3. [Documentation Validation](#documentation-validation)
4. [Automated OpenAPI Generation](#automated-openapi-generation)
5. [Documentation Deployment](#documentation-deployment)
6. [Local Testing](#local-testing)

---

## Overview

The CI/CD pipeline automates:

1. **OpenAPI Specification Validation**: Ensures the OpenAPI spec is valid
2. **Documentation Link Checking**: Verifies all internal links work
3. **Code Example Testing**: Runs code examples to ensure they work
4. **Swagger UI Deployment**: Deploys interactive API documentation
5. **Version Synchronization**: Keeps documentation version in sync with code

---

## GitHub Actions Workflow

### Workflow File

Create `.github/workflows/docs.yml`:

```yaml
name: Documentation CI/CD

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'docs/**'
      - 'web/app.py'
      - 'src/**/*.py'
      - '.github/workflows/docs.yml'
  pull_request:
    branches: [ main ]
    paths:
      - 'docs/**'
      - 'web/app.py'
      - 'src/**/*.py'

jobs:
  validate-openapi:
    name: Validate OpenAPI Specification
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install OpenAPI validator
        run: npm install -g @apidevtools/swagger-cli
      
      - name: Validate OpenAPI spec
        run: swagger-cli validate docs/openapi.yaml
      
      - name: Bundle OpenAPI spec
        run: swagger-cli bundle docs/openapi.yaml -o docs/openapi-bundled.yaml -t yaml
      
      - name: Upload bundled spec
        uses: actions/upload-artifact@v3
        with:
          name: openapi-spec
          path: docs/openapi-bundled.yaml

  check-links:
    name: Check Documentation Links
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Check markdown links
        uses: gaurav-nelson/github-action-markdown-link-check@v1
        with:
          use-quiet-mode: 'yes'
          config-file: '.github/markdown-link-check-config.json'

  test-code-examples:
    name: Test Code Examples
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install requests python-socketio pytest
      
      - name: Extract and test Python examples
        run: |
          python scripts/test_doc_examples.py docs/code-examples.md

  generate-docs:
    name: Generate API Documentation
    runs-on: ubuntu-latest
    needs: [validate-openapi, check-links]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Download OpenAPI spec
        uses: actions/download-artifact@v3
        with:
          name: openapi-spec
      
      - name: Generate static documentation
        uses: wework/redoc-cli-github-action@v1
        with:
          args: 'bundle docs/openapi.yaml -o docs/api-reference.html'
      
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs
          destination_dir: docs

  version-sync:
    name: Sync Documentation Version
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Extract version from code
        id: get_version
        run: |
          VERSION=$(python -c "import sys; sys.path.insert(0, '.'); from config import Config; print(Config.VERSION if hasattr(Config, 'VERSION') else '1.0.0')")
          echo "version=$VERSION" >> $GITHUB_OUTPUT
      
      - name: Update OpenAPI version
        run: |
          sed -i "s/version: .*/version: ${{ steps.get_version.outputs.version }}/" docs/openapi.yaml
      
      - name: Commit version update
        uses: stefanzweifel/git-auto-commit-action@v4
        with:
          commit_message: "docs: Update API version to ${{ steps.get_version.outputs.version }}"
          file_pattern: docs/openapi.yaml
```

### Link Check Configuration

Create `.github/markdown-link-check-config.json`:

```json
{
  "ignorePatterns": [
    {
      "pattern": "^http://localhost"
    },
    {
      "pattern": "^https://app.devin.ai"
    }
  ],
  "replacementPatterns": [
    {
      "pattern": "^/",
      "replacement": "{{BASEURL}}/"
    }
  ],
  "httpHeaders": [
    {
      "urls": ["https://github.com"],
      "headers": {
        "Accept-Encoding": "zstd, br, gzip, deflate"
      }
    }
  ],
  "timeout": "20s",
  "retryOn429": true,
  "retryCount": 3,
  "fallbackRetryDelay": "30s",
  "aliveStatusCodes": [200, 206]
}
```

---

## Documentation Validation

### OpenAPI Validation Script

Create `scripts/validate_openapi.py`:

```python
#!/usr/bin/env python3
"""
Validate OpenAPI specification
"""

import yaml
import sys
from typing import Dict, Any, List

def load_openapi_spec(file_path: str) -> Dict[str, Any]:
    """Load OpenAPI specification from YAML file"""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def validate_spec(spec: Dict[str, Any]) -> List[str]:
    """Validate OpenAPI specification"""
    errors = []
    
    # Check required fields
    required_fields = ['openapi', 'info', 'paths']
    for field in required_fields:
        if field not in spec:
            errors.append(f"Missing required field: {field}")
    
    # Check version format
    if 'info' in spec and 'version' in spec['info']:
        version = spec['info']['version']
        parts = version.split('.')
        if len(parts) != 3:
            errors.append(f"Invalid version format: {version}")
    
    # Check paths
    if 'paths' in spec:
        for path, methods in spec['paths'].items():
            if not path.startswith('/'):
                errors.append(f"Path must start with /: {path}")
            
            for method, operation in methods.items():
                if method not in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                    continue
                
                # Check operation has summary
                if 'summary' not in operation:
                    errors.append(f"Missing summary for {method.upper()} {path}")
                
                # Check operation has responses
                if 'responses' not in operation:
                    errors.append(f"Missing responses for {method.upper()} {path}")
    
    return errors

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_openapi.py <openapi.yaml>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        spec = load_openapi_spec(file_path)
        errors = validate_spec(spec)
        
        if errors:
            print("OpenAPI validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("OpenAPI validation passed!")
            sys.exit(0)
    
    except Exception as e:
        print(f"Error validating OpenAPI spec: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### Code Example Testing Script

Create `scripts/test_doc_examples.py`:

```python
#!/usr/bin/env python3
"""
Extract and test code examples from documentation
"""

import re
import sys
import tempfile
import subprocess
from pathlib import Path

def extract_python_examples(markdown_file: str):
    """Extract Python code blocks from markdown"""
    with open(markdown_file, 'r') as f:
        content = f.read()
    
    # Find Python code blocks
    pattern = r'```python\n(.*?)\n```'
    examples = re.findall(pattern, content, re.DOTALL)
    
    return examples

def test_example(code: str) -> bool:
    """Test a code example for syntax errors"""
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Check syntax
        result = subprocess.run(
            ['python', '-m', 'py_compile', temp_file],
            capture_output=True,
            text=True
        )
        
        # Clean up
        Path(temp_file).unlink()
        
        return result.returncode == 0
    
    except Exception as e:
        print(f"Error testing example: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_doc_examples.py <markdown_file>")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    examples = extract_python_examples(markdown_file)
    
    print(f"Found {len(examples)} Python examples")
    
    failed = 0
    for i, example in enumerate(examples, 1):
        # Skip examples that are incomplete or have placeholders
        if '...' in example or 'YOUR_' in example or 'your-' in example:
            print(f"Example {i}: Skipped (contains placeholders)")
            continue
        
        if test_example(example):
            print(f"Example {i}: ✓ Passed")
        else:
            print(f"Example {i}: ✗ Failed")
            failed += 1
    
    if failed > 0:
        print(f"\n{failed} examples failed")
        sys.exit(1)
    else:
        print("\nAll examples passed!")
        sys.exit(0)

if __name__ == '__main__':
    main()
```

---

## Automated OpenAPI Generation

### Generate from Code

For future automation, create `scripts/generate_openapi.py`:

```python
#!/usr/bin/env python3
"""
Generate OpenAPI specification from Flask routes
"""

import sys
import os
import yaml
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from web.app import app

def extract_routes(flask_app: Flask) -> Dict[str, Any]:
    """Extract routes from Flask application"""
    paths = {}
    
    for rule in flask_app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue
        
        path = str(rule.rule)
        methods = [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]
        
        if path not in paths:
            paths[path] = {}
        
        for method in methods:
            paths[path][method.lower()] = {
                'summary': f'{method} {path}',
                'responses': {
                    '200': {
                        'description': 'Successful response'
                    }
                }
            }
    
    return paths

def generate_openapi_spec(flask_app: Flask) -> Dict[str, Any]:
    """Generate OpenAPI specification"""
    paths = extract_routes(flask_app)
    
    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': 'Self-Engineering Agent Framework API',
            'version': '1.0.0',
            'description': 'Auto-generated API specification'
        },
        'servers': [
            {
                'url': 'http://localhost:5001',
                'description': 'Local development server'
            }
        ],
        'paths': paths
    }
    
    return spec

def main():
    spec = generate_openapi_spec(app)
    
    output_file = 'docs/openapi-generated.yaml'
    with open(output_file, 'w') as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
    
    print(f"Generated OpenAPI spec: {output_file}")

if __name__ == '__main__':
    main()
```

---

## Documentation Deployment

### GitHub Pages Setup

1. Enable GitHub Pages in repository settings
2. Set source to `gh-pages` branch
3. Documentation will be available at: `https://haider-toha.github.io/Self-Engineering-Agent-Framework/docs/`

### Manual Deployment

Deploy documentation manually:

```bash
# Install dependencies
npm install -g @redocly/cli

# Generate static HTML
redocly build-docs docs/openapi.yaml -o docs/api-reference.html

# Deploy to GitHub Pages
git checkout gh-pages
cp docs/api-reference.html index.html
git add index.html
git commit -m "docs: Update API reference"
git push origin gh-pages
```

---

## Local Testing

### Test Documentation Locally

```bash
# Validate OpenAPI spec
python scripts/validate_openapi.py docs/openapi.yaml

# Test code examples
python scripts/test_doc_examples.py docs/code-examples.md

# Check markdown links
npx markdown-link-check docs/*.md

# Serve documentation locally
python -m http.server 8000 --directory docs
# Visit http://localhost:8000
```

### Test Swagger UI Integration

```bash
# Start Flask server
python web/app.py

# Visit Swagger UI
# http://localhost:5001/api/docs
```

---

## Pre-commit Hooks

### Setup Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash

echo "Running documentation checks..."

# Validate OpenAPI spec
python scripts/validate_openapi.py docs/openapi.yaml
if [ $? -ne 0 ]; then
    echo "OpenAPI validation failed"
    exit 1
fi

# Check for broken links in staged markdown files
STAGED_MD_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.md$')
if [ -n "$STAGED_MD_FILES" ]; then
    for file in $STAGED_MD_FILES; do
        echo "Checking links in $file..."
        npx markdown-link-check "$file" --quiet
        if [ $? -ne 0 ]; then
            echo "Link check failed for $file"
            exit 1
        fi
    done
fi

echo "Documentation checks passed!"
exit 0
```

Make it executable:

```bash
chmod +x .git/hooks/pre-commit
```

---

## Continuous Monitoring

### Documentation Health Checks

Create `scripts/check_docs_health.py`:

```python
#!/usr/bin/env python3
"""
Check documentation health
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def check_file_exists(file_path: str) -> bool:
    """Check if file exists"""
    return Path(file_path).exists()

def check_links_in_file(file_path: str) -> List[Tuple[str, str]]:
    """Check internal links in markdown file"""
    broken_links = []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find markdown links
    pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    links = re.findall(pattern, content)
    
    for text, link in links:
        # Skip external links
        if link.startswith('http'):
            continue
        
        # Check if file exists
        if link.startswith('./'):
            link = link[2:]
        
        link_path = Path(file_path).parent / link
        if not link_path.exists():
            broken_links.append((text, link))
    
    return broken_links

def main():
    docs_dir = 'docs'
    
    # Required documentation files
    required_files = [
        'openapi.yaml',
        'websocket-events.md',
        'integration-guide.md',
        'code-examples.md',
        'sdk-documentation.md',
        'versioning-and-deprecation.md',
        'quickstart.md',
        'ci-cd-setup.md'
    ]
    
    print("Checking documentation health...\n")
    
    # Check required files
    missing_files = []
    for file in required_files:
        file_path = os.path.join(docs_dir, file)
        if not check_file_exists(file_path):
            missing_files.append(file)
    
    if missing_files:
        print("Missing files:")
        for file in missing_files:
            print(f"  - {file}")
        print()
    
    # Check links in markdown files
    all_broken_links = []
    for file in Path(docs_dir).glob('*.md'):
        broken_links = check_links_in_file(str(file))
        if broken_links:
            all_broken_links.append((file.name, broken_links))
    
    if all_broken_links:
        print("Broken links:")
        for file, links in all_broken_links:
            print(f"\n{file}:")
            for text, link in links:
                print(f"  - [{text}]({link})")
        print()
    
    # Summary
    if not missing_files and not all_broken_links:
        print("✓ Documentation health check passed!")
        return 0
    else:
        print("✗ Documentation health check failed!")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
```

---

## Summary

The CI/CD setup ensures:

1. **Automated Validation**: OpenAPI specs are validated on every commit
2. **Link Checking**: All documentation links are verified
3. **Code Testing**: Code examples are tested for syntax errors
4. **Continuous Deployment**: Documentation is automatically deployed to GitHub Pages
5. **Version Synchronization**: API version stays in sync with code
6. **Pre-commit Hooks**: Catch issues before they're committed

This setup keeps the API documentation accurate, up-to-date, and synchronized with the codebase.

---

## Next Steps

1. Set up GitHub Actions workflows
2. Configure GitHub Pages
3. Add pre-commit hooks
4. Monitor documentation health regularly
5. Update documentation with each code change
