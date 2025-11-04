# Authentication and Security Documentation

This document describes authentication, authorization, security measures, and rate limiting for the Self-Engineering Agent Framework API.

## Table of Contents

1. [Current Security Model](#current-security-model)
2. [Authentication Methods](#authentication-methods)
3. [Authorization and Access Control](#authorization-and-access-control)
4. [Rate Limiting](#rate-limiting)
5. [Security Best Practices](#security-best-practices)
6. [Production Deployment](#production-deployment)

---

## Current Security Model

### Development Mode

The Self-Engineering Agent Framework currently operates in **development mode** with the following characteristics:

- **No authentication required** for API endpoints
- **Open CORS policy** (`cors_allowed_origins="*"`)
- **Public access** to all REST and WebSocket endpoints
- **Session-based isolation** (sessions are isolated but not authenticated)

This configuration is suitable for:
- Local development and testing
- Single-user deployments
- Trusted network environments
- Research and experimentation

### Security Layers

Despite the open access model, the system implements multiple security layers:

1. **Code Execution Sandbox** - All synthesized code runs in isolated Docker containers
2. **Resource Limits** - CPU, memory, and time constraints prevent resource exhaustion
3. **Network Isolation** - Containers have no network access
4. **Filesystem Restrictions** - Read-only filesystem with limited /tmp access
5. **Input Validation** - All API inputs are validated and sanitized

---

## Authentication Methods

### Recommended for Production

When deploying to production, implement one or more of the following authentication methods:

#### 1. API Key Authentication

Simple token-based authentication for programmatic access.

**Implementation:**

```python
# web/app.py - Add authentication middleware

from functools import wraps
from flask import request, jsonify
import os

API_KEYS = set(os.getenv('API_KEYS', '').split(','))

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key required'
            }), 401
        
        if api_key not in API_KEYS:
            return jsonify({
                'success': False,
                'error': 'Invalid API key'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

# Apply to endpoints
@ns_session.route('')
class SessionResource(Resource):
    @require_api_key
    @ns_session.doc('create_session')
    def post(self):
        # ... existing code
```

**Client Usage:**

```python
import requests

headers = {
    'X-API-Key': 'your-api-key-here'
}

response = requests.post(
    'http://localhost:5001/api/session',
    headers=headers
)
```

**Environment Configuration:**

```bash
# .env
API_KEYS=key1,key2,key3
```

#### 2. JWT (JSON Web Token) Authentication

Stateless token-based authentication with expiration and claims.

**Implementation:**

```python
# requirements.txt - Add dependency
PyJWT>=2.8.0

# web/app.py
import jwt
from datetime import datetime, timedelta
from functools import wraps

JWT_SECRET = os.getenv('JWT_SECRET', 'change-me-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

def generate_token(user_id: str, session_id: str = None) -> str:
    """Generate JWT token"""
    payload = {
        'user_id': user_id,
        'session_id': session_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def require_jwt(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Token required'
            }), 401
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.user_id = payload['user_id']
            request.session_id = payload.get('session_id')
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': 'Token expired'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'error': 'Invalid token'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

# Login endpoint
@ns_session.route('/login')
class LoginResource(Resource):
    def post(self):
        data = request.get_json()
        user_id = data.get('user_id')
        
        # Validate credentials (implement your logic)
        if not validate_credentials(user_id, data.get('password')):
            return {'success': False, 'error': 'Invalid credentials'}, 401
        
        token = generate_token(user_id)
        return {'success': True, 'token': token}
```

**Client Usage:**

```python
# Login
response = requests.post('http://localhost:5001/api/session/login', json={
    'user_id': 'user123',
    'password': 'password'
})
token = response.json()['token']

# Use token
headers = {
    'Authorization': f'Bearer {token}'
}

response = requests.post(
    'http://localhost:5001/api/session',
    headers=headers
)
```

#### 3. OAuth 2.0 / OpenID Connect

Enterprise-grade authentication with third-party identity providers.

**Recommended Providers:**
- Auth0
- Okta
- Google OAuth
- GitHub OAuth
- Azure AD

**Implementation with Auth0:**

```python
# requirements.txt
authlib>=1.3.0

# web/app.py
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)

oauth.register(
    'auth0',
    client_id=os.getenv('AUTH0_CLIENT_ID'),
    client_secret=os.getenv('AUTH0_CLIENT_SECRET'),
    server_metadata_url=f'https://{os.getenv("AUTH0_DOMAIN")}/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email'
    }
)

@app.route('/login')
def login():
    redirect_uri = url_for('callback', _external=True)
    return oauth.auth0.authorize_redirect(redirect_uri)

@app.route('/callback')
def callback():
    token = oauth.auth0.authorize_access_token()
    user_info = token['userinfo']
    
    # Create session with user context
    session['user_id'] = user_info['sub']
    
    return redirect('/')

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function
```

#### 4. Session-Based Authentication

Traditional cookie-based authentication for web applications.

**Implementation:**

```python
# web/app.py
from flask import session
from werkzeug.security import check_password_hash

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me-in-production')
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user_id = data.get('user_id')
    password = data.get('password')
    
    # Validate credentials
    if validate_user(user_id, password):
        session['user_id'] = user_id
        session['authenticated'] = True
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function
```

---

## Authorization and Access Control

### Role-Based Access Control (RBAC)

Implement different permission levels for different user types.

**Roles:**

| Role | Permissions |
|------|-------------|
| **Admin** | Full access: create/delete tools, view all sessions, manage users |
| **Developer** | Create tools, view own sessions, execute tools |
| **User** | Execute existing tools, view own sessions |
| **Guest** | Read-only access to public tools |

**Implementation:**

```python
# models/user.py
from enum import Enum

class Role(Enum):
    ADMIN = 'admin'
    DEVELOPER = 'developer'
    USER = 'user'
    GUEST = 'guest'

ROLE_PERMISSIONS = {
    Role.ADMIN: {'create_tool', 'delete_tool', 'view_all_sessions', 'manage_users'},
    Role.DEVELOPER: {'create_tool', 'view_own_sessions', 'execute_tool'},
    Role.USER: {'execute_tool', 'view_own_sessions'},
    Role.GUEST: {'view_public_tools'}
}

def require_permission(permission: str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = get_user_role(request.user_id)
            
            if permission not in ROLE_PERMISSIONS.get(user_role, set()):
                return jsonify({
                    'success': False,
                    'error': 'Insufficient permissions'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage
@ns_tools.route('/<string:tool_name>')
class ToolDetailResource(Resource):
    @require_jwt
    @require_permission('delete_tool')
    def delete(self, tool_name):
        # Delete tool implementation
        pass
```

### Row-Level Security (RLS)

Implement database-level access control using Supabase RLS policies.

**Supabase RLS Policies:**

```sql
-- Enable RLS on tables
ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_executions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own sessions
CREATE POLICY session_isolation ON agent_sessions
    FOR ALL
    USING (
        session_id IN (
            SELECT session_id FROM user_sessions 
            WHERE user_id = current_setting('app.current_user_id')
        )
    );

-- Policy: Users can only see their own messages
CREATE POLICY message_isolation ON session_messages
    FOR ALL
    USING (
        session_id IN (
            SELECT session_id FROM user_sessions 
            WHERE user_id = current_setting('app.current_user_id')
        )
    );

-- Policy: Users can only see their own executions
CREATE POLICY execution_isolation ON tool_executions
    FOR ALL
    USING (
        session_id IN (
            SELECT session_id FROM user_sessions 
            WHERE user_id = current_setting('app.current_user_id')
        )
    );

-- Policy: All users can read public tools
CREATE POLICY public_tools ON agent_tools
    FOR SELECT
    USING (true);

-- Policy: Only admins can delete tools
CREATE POLICY admin_delete_tools ON agent_tools
    FOR DELETE
    USING (
        current_setting('app.user_role') = 'admin'
    );
```

**Application Integration:**

```python
# Set user context for RLS
def set_user_context(user_id: str, role: str):
    supabase.rpc('set_user_context', {
        'user_id': user_id,
        'role': role
    }).execute()

# Before each request
@app.before_request
def before_request():
    if hasattr(request, 'user_id'):
        set_user_context(request.user_id, get_user_role(request.user_id))
```

---

## Rate Limiting

### Implementation Strategies

#### 1. Flask-Limiter (Recommended)

Simple rate limiting for Flask applications.

**Installation:**

```bash
pip install Flask-Limiter
```

**Implementation:**

```python
# web/app.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379"  # Or use memory://
)

# Apply to specific endpoints
@ns_session.route('')
class SessionResource(Resource):
    @limiter.limit("10 per minute")
    def post(self):
        # Create session
        pass

# Different limits for different endpoints
@app.route('/api/query')
@limiter.limit("30 per minute")
def query():
    pass

# Exempt certain endpoints
@app.route('/api/health')
@limiter.exempt
def health():
    return {'status': 'ok'}
```

#### 2. Token Bucket Algorithm

Custom implementation for fine-grained control.

**Implementation:**

```python
# utils/rate_limiter.py
import time
from collections import defaultdict
from threading import Lock

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

class RateLimiter:
    def __init__(self):
        self.buckets = defaultdict(lambda: TokenBucket(capacity=100, refill_rate=1.0))
    
    def check_limit(self, key: str, tokens: int = 1) -> bool:
        return self.buckets[key].consume(tokens)

rate_limiter = RateLimiter()

# Middleware
def rate_limit_middleware(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = getattr(request, 'user_id', get_remote_address())
        
        if not rate_limiter.check_limit(user_id):
            return jsonify({
                'success': False,
                'error': 'Rate limit exceeded'
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function
```

#### 3. Redis-Based Rate Limiting

Distributed rate limiting for multi-instance deployments.

**Implementation:**

```python
# utils/redis_limiter.py
import redis
import time

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def check_rate_limit(key: str, limit: int, window: int) -> bool:
    """
    Check rate limit using sliding window
    
    Args:
        key: Unique identifier (user_id, IP, etc.)
        limit: Maximum requests allowed
        window: Time window in seconds
    
    Returns:
        True if request is allowed, False otherwise
    """
    now = time.time()
    window_start = now - window
    
    pipe = redis_client.pipeline()
    
    # Remove old entries
    pipe.zremrangebyscore(key, 0, window_start)
    
    # Count requests in window
    pipe.zcard(key)
    
    # Add current request
    pipe.zadd(key, {str(now): now})
    
    # Set expiration
    pipe.expire(key, window)
    
    results = pipe.execute()
    request_count = results[1]
    
    return request_count < limit

# Usage
def rate_limit(limit: int, window: int):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = getattr(request, 'user_id', get_remote_address())
            key = f"rate_limit:{user_id}"
            
            if not check_rate_limit(key, limit, window):
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'retry_after': window
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Apply to endpoints
@app.route('/api/query')
@rate_limit(limit=30, window=60)  # 30 requests per minute
def query():
    pass
```

### Rate Limit Tiers

Implement different rate limits for different user tiers:

```python
RATE_LIMITS = {
    Role.GUEST: {'requests_per_hour': 10, 'synthesis_per_day': 0},
    Role.USER: {'requests_per_hour': 100, 'synthesis_per_day': 5},
    Role.DEVELOPER: {'requests_per_hour': 500, 'synthesis_per_day': 50},
    Role.ADMIN: {'requests_per_hour': 10000, 'synthesis_per_day': 1000}
}

def get_rate_limit(user_id: str) -> dict:
    role = get_user_role(user_id)
    return RATE_LIMITS.get(role, RATE_LIMITS[Role.GUEST])
```

### Rate Limit Headers

Include rate limit information in response headers:

```python
@app.after_request
def add_rate_limit_headers(response):
    if hasattr(request, 'user_id'):
        limits = get_rate_limit(request.user_id)
        remaining = get_remaining_requests(request.user_id)
        
        response.headers['X-RateLimit-Limit'] = str(limits['requests_per_hour'])
        response.headers['X-RateLimit-Remaining'] = str(remaining)
        response.headers['X-RateLimit-Reset'] = str(get_reset_time())
    
    return response
```

---

## Security Best Practices

### 1. Environment Variables

Never hardcode secrets in source code:

```bash
# .env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...
JWT_SECRET=random-secure-string
API_KEYS=key1,key2,key3
AUTH0_CLIENT_ID=...
AUTH0_CLIENT_SECRET=...
```

### 2. HTTPS Only

Always use HTTPS in production:

```python
# Force HTTPS
@app.before_request
def force_https():
    if not request.is_secure and app.env == 'production':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
```

### 3. CORS Configuration

Restrict CORS to specific origins:

```python
# web/app.py
from flask_cors import CORS

ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')

CORS(app, origins=ALLOWED_ORIGINS)

socketio = SocketIO(
    app,
    cors_allowed_origins=ALLOWED_ORIGINS,
    async_mode='eventlet'
)
```

### 4. Input Validation

Validate all user inputs:

```python
from marshmallow import Schema, fields, validate, ValidationError

class QuerySchema(Schema):
    prompt = fields.Str(required=True, validate=validate.Length(min=1, max=1000))
    session_id = fields.Str(required=True, validate=validate.Regexp(r'^[a-f0-9-]{36}$'))

def validate_input(schema_class):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            schema = schema_class()
            try:
                data = schema.load(request.get_json())
                request.validated_data = data
            except ValidationError as err:
                return jsonify({
                    'success': False,
                    'error': 'Validation error',
                    'details': err.messages
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### 5. SQL Injection Prevention

Use parameterized queries (already implemented in Supabase client):

```python
# Good - parameterized
supabase.table('agent_tools').select('*').eq('name', tool_name).execute()

# Bad - string concatenation (never do this)
# query = f"SELECT * FROM agent_tools WHERE name = '{tool_name}'"
```

### 6. Logging and Monitoring

Log security events:

```python
import logging

security_logger = logging.getLogger('security')

@app.before_request
def log_request():
    security_logger.info(
        f"Request: {request.method} {request.path} "
        f"from {get_remote_address()} "
        f"user={getattr(request, 'user_id', 'anonymous')}"
    )

def log_security_event(event_type: str, details: dict):
    security_logger.warning(
        f"Security event: {event_type}",
        extra={'details': details}
    )

# Usage
if not validate_api_key(api_key):
    log_security_event('invalid_api_key', {
        'ip': get_remote_address(),
        'key': api_key[:8] + '...'
    })
```

---

## Production Deployment

### Deployment Checklist

- [ ] Enable authentication (API key, JWT, or OAuth)
- [ ] Configure HTTPS with valid SSL certificate
- [ ] Set secure environment variables
- [ ] Restrict CORS to specific origins
- [ ] Enable rate limiting
- [ ] Implement role-based access control
- [ ] Enable Supabase RLS policies
- [ ] Configure secure session cookies
- [ ] Set up logging and monitoring
- [ ] Enable firewall rules
- [ ] Configure backup strategy
- [ ] Set up intrusion detection
- [ ] Implement audit logging
- [ ] Configure DDoS protection

### Example Production Configuration

```python
# config.py
import os

class ProductionConfig:
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET = os.getenv('JWT_SECRET')
    
    # Flask
    FLASK_ENV = 'production'
    FLASK_DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # CORS
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL')
    
    # Authentication
    AUTH_ENABLED = True
    AUTH_METHOD = os.getenv('AUTH_METHOD', 'jwt')  # 'jwt', 'oauth', 'api_key'
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = '/var/log/agent/app.log'
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user
RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "--worker-class", "eventlet", "web.app:app"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## Summary

The Self-Engineering Agent Framework provides a flexible foundation for implementing various authentication and security models. For production deployments, we recommend:

1. **Authentication**: JWT or OAuth 2.0 for API access
2. **Authorization**: Role-based access control with Supabase RLS
3. **Rate Limiting**: Redis-based distributed rate limiting
4. **Security**: HTTPS, input validation, secure environment variables
5. **Monitoring**: Comprehensive logging and audit trails

Choose the authentication method that best fits your deployment scenario and scale requirements.
