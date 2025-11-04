# Authentication and Security Documentation

## Overview

This document provides comprehensive information about authentication, security, and rate limiting for the Self-Engineering Agent Framework. While the current implementation focuses on local development, this guide covers best practices for production deployments.

## Table of Contents

1. [Current Authentication Model](#current-authentication-model)
2. [Environment Variables and Credentials](#environment-variables-and-credentials)
3. [Production Authentication Recommendations](#production-authentication-recommendations)
4. [Rate Limiting](#rate-limiting)
5. [Security Best Practices](#security-best-practices)
6. [Docker Sandbox Security](#docker-sandbox-security)
7. [API Security](#api-security)

---

## Current Authentication Model

### Development Mode

The Self-Engineering Agent Framework currently operates in **development mode** without authentication requirements for the REST API and WebSocket endpoints. This is suitable for:

- Local development
- Testing and evaluation
- Single-user deployments
- Trusted network environments

**Current Access Model:**
- No API keys required for REST endpoints
- No authentication for WebSocket connections
- Open CORS policy (`cors_allowed_origins="*"`)
- No rate limiting enforced

### Security Layers

While the API is open in development mode, the framework implements several security layers:

1. **Docker Sandbox Isolation**: All user-generated code runs in isolated Docker containers
2. **Network Isolation**: Sandbox containers have no network access
3. **Resource Limits**: CPU, memory, and execution time limits
4. **Filesystem Restrictions**: Read-only filesystem with limited /tmp access
5. **Non-root Execution**: Code runs as non-privileged user

---

## Environment Variables and Credentials

### Required Credentials

The framework requires the following credentials to operate:

#### 1. OpenAI API Key

**Purpose**: Required for all LLM operations including tool synthesis, embeddings, and natural language processing.

**Setup:**
```bash
# In .env file
OPENAI_API_KEY=sk-your-openai-api-key-here

# Or as environment variable
export OPENAI_API_KEY=sk-your-openai-api-key-here
```

**Usage:**
- Tool specification generation
- Test generation
- Implementation generation
- Argument extraction
- Embedding generation (1536-dim vectors)
- Natural language response synthesis

**Security Notes:**
- Never commit API keys to version control
- Use `.env` files (excluded via `.gitignore`)
- Rotate keys regularly
- Monitor usage and costs
- Set spending limits in OpenAI dashboard

#### 2. Supabase Credentials

**Purpose**: Required for database operations including tool storage, execution logging, and session management.

**Setup:**
```bash
# In .env file
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key

# Or as environment variables
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_KEY=your-supabase-anon-or-service-key
```

**Key Types:**
- **Anon Key**: For client-side access with Row Level Security (RLS)
- **Service Role Key**: For server-side access with full permissions (recommended for this framework)

**Security Notes:**
- Use service role key for backend operations
- Never expose service role key to clients
- Enable Row Level Security (RLS) policies if using anon key
- Restrict database access by IP if possible
- Monitor database access logs

### Configuration File

**File**: `config.py`

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
    OPENAI_EMBEDDING_MODEL = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.4'))
    
    # Docker Sandbox Configuration
    DOCKER_IMAGE_NAME = os.getenv('DOCKER_IMAGE_NAME', 'agent-sandbox:latest')
    DOCKER_TIMEOUT = int(os.getenv('DOCKER_TIMEOUT', '30'))
    
    # Storage Configuration
    TOOLS_DIR = os.getenv('TOOLS_DIR', 'tools/')
    
    # Flask Configuration
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', '5001'))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'self-engineering-agent-secret-key')
```

### Environment File Template

**File**: `.env.example`

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key-here
SIMILARITY_THRESHOLD=0.4

# Docker Sandbox Configuration
DOCKER_IMAGE_NAME=agent-sandbox:latest
DOCKER_TIMEOUT=30

# Storage Configuration
TOOLS_DIR=tools/

# Flask Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5001
FLASK_DEBUG=True
FLASK_SECRET_KEY=change-this-in-production
```

---

## Production Authentication Recommendations

### 1. API Key Authentication

For production deployments, implement API key authentication:

#### Implementation Example

```python
# web/app.py
from functools import wraps
from flask import request, jsonify
import os

# Load API keys from environment
VALID_API_KEYS = set(os.getenv('API_KEYS', '').split(','))

def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key required'
            }), 401
        
        if api_key not in VALID_API_KEYS:
            return jsonify({
                'success': False,
                'error': 'Invalid API key'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function

# Apply to endpoints
@app.route('/api/tools', methods=['GET'])
@require_api_key
def get_tools():
    # ... existing code ...
```

#### Client Usage

```python
import requests

headers = {
    'X-API-Key': 'your-api-key-here',
    'Content-Type': 'application/json'
}

response = requests.get('http://localhost:5001/api/tools', headers=headers)
```

```bash
# cURL
curl -H "X-API-Key: your-api-key-here" http://localhost:5001/api/tools
```

### 2. JWT Authentication

For more sophisticated authentication, implement JWT tokens:

#### Implementation Example

```python
import jwt
from datetime import datetime, timedelta
from functools import wraps

SECRET_KEY = os.getenv('JWT_SECRET_KEY')

def generate_token(user_id):
    """Generate JWT token."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def require_jwt(f):
    """Decorator to require JWT authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'Token required'}), 401
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function
```

### 3. OAuth 2.0 Integration

For enterprise deployments, integrate with OAuth 2.0 providers:

- Google OAuth
- GitHub OAuth
- Microsoft Azure AD
- Custom OAuth server

**Recommended Library**: `authlib`

```bash
pip install authlib
```

### 4. WebSocket Authentication

Implement authentication for Socket.IO connections:

```python
from flask_socketio import disconnect

@socketio.on('connect')
def handle_connect():
    """Handle client connection with authentication."""
    token = request.args.get('token')
    
    if not token or not validate_token(token):
        disconnect()
        return False
    
    print('Authenticated client connected')
    emit('connected', {'data': 'Connected to agent'})
```

**Client Usage:**

```javascript
const socket = io('http://localhost:5001', {
  query: {
    token: 'your-auth-token-here'
  }
});
```

---

## Rate Limiting

### Why Rate Limiting?

Rate limiting is essential for:
- Preventing abuse and DoS attacks
- Managing OpenAI API costs
- Ensuring fair resource allocation
- Protecting database performance

### Implementation with Flask-Limiter

```bash
pip install Flask-Limiter
```

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379"
)

# Apply to specific endpoints
@app.route('/api/tools', methods=['GET'])
@limiter.limit("100 per hour")
def get_tools():
    # ... existing code ...

@app.route('/api/session', methods=['POST'])
@limiter.limit("10 per hour")
def create_session():
    # ... existing code ...

# WebSocket rate limiting
@socketio.on('query')
@limiter.limit("20 per hour")
def handle_query(data):
    # ... existing code ...
```

### Rate Limit Tiers

**Recommended Limits:**

| Endpoint | Free Tier | Pro Tier | Enterprise |
|----------|-----------|----------|------------|
| GET /api/tools | 100/hour | 1000/hour | Unlimited |
| POST /api/session | 10/hour | 100/hour | Unlimited |
| WebSocket query | 20/hour | 200/hour | Unlimited |
| GET /api/analytics/* | 50/hour | 500/hour | Unlimited |

### Custom Rate Limiting by API Key

```python
def get_api_key():
    """Extract API key from request."""
    return request.headers.get('X-API-Key', get_remote_address())

limiter = Limiter(
    app=app,
    key_func=get_api_key,
    storage_uri="redis://localhost:6379"
)

# Different limits per API key tier
@app.route('/api/tools', methods=['GET'])
@limiter.limit("100 per hour", key_func=lambda: get_tier_limit())
def get_tools():
    # ... existing code ...
```

### Rate Limit Headers

Include rate limit information in response headers:

```python
from flask import make_response

@app.after_request
def add_rate_limit_headers(response):
    """Add rate limit headers to response."""
    if hasattr(request, 'rate_limit'):
        response.headers['X-RateLimit-Limit'] = request.rate_limit.limit
        response.headers['X-RateLimit-Remaining'] = request.rate_limit.remaining
        response.headers['X-RateLimit-Reset'] = request.rate_limit.reset
    return response
```

---

## Security Best Practices

### 1. HTTPS/TLS

**Always use HTTPS in production:**

```python
# Force HTTPS
@app.before_request
def force_https():
    if not request.is_secure and not app.debug:
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
```

**Use a reverse proxy (nginx) for TLS termination:**

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket support
    location /socket.io {
        proxy_pass http://localhost:5001/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. CORS Configuration

**Restrict CORS in production:**

```python
from flask_cors import CORS

# Development (permissive)
if app.debug:
    CORS(app, origins="*")
else:
    # Production (restrictive)
    CORS(app, origins=[
        "https://your-domain.com",
        "https://app.your-domain.com"
    ])

# Socket.IO CORS
socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "https://your-domain.com",
        "https://app.your-domain.com"
    ] if not app.debug else "*"
)
```

### 3. Input Validation

**Validate all user inputs:**

```python
from flask import request
import re

def validate_tool_name(name):
    """Validate tool name format."""
    if not re.match(r'^[a-z_][a-z0-9_]*$', name):
        raise ValueError('Invalid tool name format')
    if len(name) > 100:
        raise ValueError('Tool name too long')
    return name

def validate_session_id(session_id):
    """Validate session ID format (UUID)."""
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, session_id):
        raise ValueError('Invalid session ID format')
    return session_id

@app.route('/api/tools/<tool_name>', methods=['GET'])
def get_tool_details(tool_name):
    try:
        tool_name = validate_tool_name(tool_name)
        # ... existing code ...
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
```

### 4. SQL Injection Prevention

**Use parameterized queries (already implemented via Supabase client):**

```python
# Good (parameterized)
result = supabase.table('agent_tools').select('*').eq('name', tool_name).execute()

# Bad (string concatenation - NEVER DO THIS)
# query = f"SELECT * FROM agent_tools WHERE name = '{tool_name}'"
```

### 5. Secret Management

**Use environment variables and secret managers:**

```python
# Development: .env file
from dotenv import load_dotenv
load_dotenv()

# Production: AWS Secrets Manager
import boto3
import json

def get_secret(secret_name):
    """Retrieve secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Or use HashiCorp Vault, Azure Key Vault, etc.
```

### 6. Logging and Monitoring

**Implement comprehensive logging:**

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
handler = RotatingFileHandler('app.log', maxBytes=10000000, backupCount=5)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# Log security events
@app.before_request
def log_request():
    app.logger.info(f"{request.method} {request.path} - {request.remote_addr}")

# Log authentication failures
def log_auth_failure(reason, ip_address):
    app.logger.warning(f"Auth failure: {reason} from {ip_address}")
```

---

## Docker Sandbox Security

The framework implements a 5-layer security model for code execution:

### 1. Container Isolation

**Kernel-level process isolation:**
- Each tool execution runs in a separate Docker container
- Containers are destroyed after execution
- No shared state between executions

### 2. Network Isolation

**No network access:**
```python
container = client.containers.run(
    image=DOCKER_IMAGE_NAME,
    command=command,
    network_mode='none',  # No network access
    # ... other settings ...
)
```

### 3. Resource Limits

**CPU, memory, and time constraints:**
```python
container = client.containers.run(
    image=DOCKER_IMAGE_NAME,
    mem_limit='512m',      # 512MB RAM limit
    cpu_quota=50000,       # 50% CPU limit
    timeout=30,            # 30 second timeout
    # ... other settings ...
)
```

### 4. Filesystem Restrictions

**Read-only filesystem with limited /tmp:**
```python
container = client.containers.run(
    image=DOCKER_IMAGE_NAME,
    read_only=True,        # Read-only root filesystem
    tmpfs={'/tmp': 'size=100m'},  # Limited /tmp space
    # ... other settings ...
)
```

### 5. Non-root Execution

**Run as unprivileged user:**
```dockerfile
# In Dockerfile
RUN useradd -m -u 1000 agent
USER agent
```

### Security Recommendations

1. **Keep Docker images updated**: Regularly rebuild sandbox images with security patches
2. **Scan images for vulnerabilities**: Use tools like `docker scan` or Trivy
3. **Limit available packages**: Only include necessary Python packages in sandbox
4. **Monitor resource usage**: Track CPU, memory, and execution time metrics
5. **Implement execution quotas**: Limit number of executions per user/session

---

## API Security

### 1. Content Security Policy

```python
@app.after_request
def set_security_headers(response):
    """Set security headers."""
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

### 2. Request Size Limits

```python
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size
```

### 3. Timeout Configuration

```python
# Gunicorn configuration
timeout = 120  # 2 minutes
graceful_timeout = 30
keepalive = 5
```

### 4. Error Handling

**Never expose internal errors to clients:**

```python
@app.errorhandler(Exception)
def handle_error(error):
    """Handle all errors."""
    app.logger.error(f"Error: {error}", exc_info=True)
    
    if app.debug:
        # Development: show detailed error
        return jsonify({'error': str(error)}), 500
    else:
        # Production: generic error message
        return jsonify({'error': 'Internal server error'}), 500
```

---

## Security Checklist

### Development

- [ ] Use `.env` file for credentials
- [ ] Never commit secrets to version control
- [ ] Use `.gitignore` to exclude `.env` files
- [ ] Test with limited OpenAI credits
- [ ] Use development Supabase project

### Production

- [ ] Enable HTTPS/TLS
- [ ] Implement authentication (API keys or JWT)
- [ ] Configure rate limiting
- [ ] Restrict CORS origins
- [ ] Use secret manager for credentials
- [ ] Enable security headers
- [ ] Implement comprehensive logging
- [ ] Set up monitoring and alerts
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Use production Supabase project with RLS
- [ ] Configure firewall rules
- [ ] Implement backup strategy
- [ ] Set up intrusion detection
- [ ] Document incident response procedures

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Supabase Security](https://supabase.com/docs/guides/auth)
- [OpenAI API Best Practices](https://platform.openai.com/docs/guides/safety-best-practices)
