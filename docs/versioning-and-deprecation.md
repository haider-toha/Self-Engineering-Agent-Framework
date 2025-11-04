# API Versioning Strategy and Deprecation Policy

This document outlines the versioning strategy and deprecation policy for the Self-Engineering Agent Framework API to ensure backward compatibility and smooth transitions as the framework evolves.

## Table of Contents

1. [Versioning Strategy](#versioning-strategy)
2. [Semantic Versioning](#semantic-versioning)
3. [API Version Management](#api-version-management)
4. [Deprecation Policy](#deprecation-policy)
5. [Breaking Changes](#breaking-changes)
6. [Migration Guide](#migration-guide)
7. [Version Support Timeline](#version-support-timeline)

---

## Versioning Strategy

The Self-Engineering Agent Framework follows **Semantic Versioning 2.0.0** (semver.org) for all releases.

### Version Format

```
MAJOR.MINOR.PATCH
```

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible functionality additions
- **PATCH**: Backward-compatible bug fixes

### Current Version

**Version 1.0.0** (Initial Release)

---

## Semantic Versioning

### MAJOR Version (X.0.0)

Incremented when making incompatible API changes:

- Removing REST endpoints
- Changing endpoint URLs
- Removing required parameters
- Changing response structure in breaking ways
- Removing WebSocket event types
- Changing event payload structure in breaking ways

**Example**: 1.0.0 → 2.0.0

### MINOR Version (1.X.0)

Incremented when adding functionality in a backward-compatible manner:

- Adding new REST endpoints
- Adding optional parameters to existing endpoints
- Adding new WebSocket event types
- Adding new fields to response payloads (non-breaking)
- Adding new features to existing tools

**Example**: 1.0.0 → 1.1.0

### PATCH Version (1.0.X)

Incremented when making backward-compatible bug fixes:

- Fixing bugs in existing functionality
- Performance improvements
- Security patches
- Documentation updates

**Example**: 1.0.0 → 1.0.1

---

## API Version Management

### URL-Based Versioning

Starting from version 2.0.0, the API will support URL-based versioning:

```
# Version 1 (current - no version prefix)
http://localhost:5001/api/tools

# Version 2 (future)
http://localhost:5001/api/v2/tools

# Version 3 (future)
http://localhost:5001/api/v3/tools
```

### Version Header

Clients can optionally specify the API version via header:

```http
GET /api/tools HTTP/1.1
Host: localhost:5001
X-API-Version: 1.0
```

### Default Version

If no version is specified, the API defaults to the latest stable version.

### Version Discovery

Clients can discover available API versions:

```http
GET /api/versions HTTP/1.1
```

**Response**:
```json
{
    "current": "1.0.0",
    "supported": ["1.0.0"],
    "deprecated": [],
    "sunset": []
}
```

---

## Deprecation Policy

### Deprecation Timeline

When a feature is deprecated, it follows this timeline:

1. **Announcement** (T+0): Feature marked as deprecated in documentation
2. **Warning Period** (T+0 to T+6 months): Feature continues to work with deprecation warnings
3. **Sunset Period** (T+6 to T+12 months): Feature still works but may be removed
4. **Removal** (T+12 months): Feature is removed in next major version

### Deprecation Notices

Deprecated features are indicated in multiple ways:

#### 1. HTTP Headers

```http
HTTP/1.1 200 OK
X-API-Deprecated: true
X-API-Sunset: 2026-11-04T00:00:00Z
X-API-Deprecation-Info: https://docs.example.com/deprecation/endpoint-name
```

#### 2. Response Metadata

```json
{
    "success": true,
    "data": {...},
    "_deprecated": {
        "deprecated": true,
        "sunset_date": "2026-11-04T00:00:00Z",
        "alternative": "/api/v2/new-endpoint",
        "message": "This endpoint is deprecated. Please migrate to /api/v2/new-endpoint"
    }
}
```

#### 3. WebSocket Events

```json
{
    "event_type": "deprecation_warning",
    "data": {
        "feature": "old_event_type",
        "sunset_date": "2026-11-04T00:00:00Z",
        "alternative": "new_event_type",
        "message": "The 'old_event_type' event is deprecated"
    }
}
```

#### 4. Documentation

All deprecated features are clearly marked in the documentation:

```markdown
## GET /api/old-endpoint

**⚠️ DEPRECATED**: This endpoint is deprecated as of v1.5.0 and will be removed in v2.0.0.
Please use `/api/v2/new-endpoint` instead.

**Sunset Date**: 2026-11-04
```

---

## Breaking Changes

### What Constitutes a Breaking Change

The following are considered breaking changes and require a MAJOR version bump:

#### REST API

- Removing an endpoint
- Changing endpoint URL structure
- Removing a required parameter
- Changing parameter types (e.g., string → integer)
- Removing fields from response payload
- Changing response status codes for existing scenarios
- Changing authentication requirements

#### WebSocket API

- Removing an event type
- Changing event payload structure (removing fields)
- Changing event emission order in critical flows
- Changing connection requirements

#### Tool Synthesis

- Changing tool naming conventions
- Changing tool signature generation
- Removing support for existing tool patterns

### Non-Breaking Changes

The following are NOT considered breaking changes:

- Adding new endpoints
- Adding optional parameters
- Adding new fields to responses
- Adding new event types
- Improving error messages
- Performance improvements
- Bug fixes

---

## Migration Guide

### Version 1.x to 2.0 (Future)

When version 2.0 is released, this section will provide detailed migration instructions.

**Planned Changes for v2.0**:

1. **URL Versioning**: All endpoints will be prefixed with `/api/v2/`
2. **Authentication**: API key authentication will be required
3. **Rate Limiting**: Rate limits will be enforced
4. **Pagination**: All list endpoints will use cursor-based pagination
5. **WebSocket Namespaces**: Events will be organized into namespaces

**Migration Steps**:

```python
# Version 1.x (current)
response = requests.get('http://localhost:5001/api/tools')

# Version 2.0 (future)
response = requests.get(
    'http://localhost:5001/api/v2/tools',
    headers={'Authorization': 'Bearer YOUR_API_KEY'}
)
```

### Backward Compatibility Mode

Version 2.0 will support a backward compatibility mode for 12 months:

```python
# Enable v1 compatibility mode
response = requests.get(
    'http://localhost:5001/api/v2/tools',
    headers={'X-API-Compatibility': 'v1'}
)
```

---

## Version Support Timeline

### Support Levels

- **Active Support**: Full support with new features and bug fixes
- **Maintenance Support**: Security patches and critical bug fixes only
- **End of Life**: No support, deprecated

### Version Support Schedule

| Version | Release Date | Active Support Until | Maintenance Support Until | End of Life |
|---------|--------------|----------------------|---------------------------|-------------|
| 1.0.0   | 2025-11-04   | 2026-11-04          | 2027-11-04               | 2028-11-04  |
| 2.0.0   | TBD          | TBD                 | TBD                      | TBD         |

### Support Policy

- **Active Support**: 12 months from release
- **Maintenance Support**: Additional 12 months (24 months total)
- **End of Life**: 36 months from release

---

## Deprecation Examples

### Example 1: Deprecating an Endpoint

**Scenario**: The `/api/tools` endpoint is being replaced with `/api/v2/capabilities`

**Timeline**:

1. **v1.5.0** (2026-05-04): Deprecation announced
   - `/api/tools` marked as deprecated
   - Deprecation headers added to responses
   - Documentation updated

2. **v1.5.0 - v1.11.0** (2026-05-04 to 2026-11-04): Warning period
   - Endpoint continues to work normally
   - Deprecation warnings in responses
   - Migration guide published

3. **v1.11.0 - v1.23.0** (2026-11-04 to 2027-05-04): Sunset period
   - Endpoint still works but may be removed
   - Increased warning frequency
   - Sunset date announced

4. **v2.0.0** (2027-05-04): Removal
   - `/api/tools` removed
   - Only `/api/v2/capabilities` available

**Migration Code**:

```python
# Old (deprecated)
response = requests.get('http://localhost:5001/api/tools')

# New (recommended)
response = requests.get('http://localhost:5001/api/v2/capabilities')
```

### Example 2: Deprecating a WebSocket Event

**Scenario**: The `tool_found` event is being replaced with `capability_discovered`

**Timeline**:

1. **v1.6.0**: Deprecation announced
   - Both events emitted simultaneously
   - `tool_found` marked as deprecated
   - Deprecation warning event emitted

2. **v1.6.0 - v1.12.0**: Warning period
   - Both events continue to be emitted
   - Clients encouraged to migrate

3. **v2.0.0**: Removal
   - Only `capability_discovered` emitted

**Migration Code**:

```javascript
// Old (deprecated)
socket.on('tool_found', (data) => {
    console.log(`Found tool: ${data.tool_name}`);
});

// New (recommended)
socket.on('capability_discovered', (data) => {
    console.log(`Discovered capability: ${data.capability_name}`);
});
```

### Example 3: Deprecating a Parameter

**Scenario**: The `threshold` parameter in `/api/tools` is being renamed to `similarity_threshold`

**Timeline**:

1. **v1.7.0**: Deprecation announced
   - Both parameters accepted
   - `threshold` marked as deprecated
   - Deprecation warning in response

2. **v1.7.0 - v1.13.0**: Warning period
   - Both parameters work
   - `threshold` maps to `similarity_threshold` internally

3. **v2.0.0**: Removal
   - Only `similarity_threshold` accepted

**Migration Code**:

```python
# Old (deprecated)
response = requests.get(
    'http://localhost:5001/api/tools',
    params={'threshold': 0.7}
)

# New (recommended)
response = requests.get(
    'http://localhost:5001/api/tools',
    params={'similarity_threshold': 0.7}
)
```

---

## Change Log

All changes are documented in the CHANGELOG.md file following the Keep a Changelog format.

### Change Log Format

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New features that have been added

### Changed
- Changes in existing functionality

### Deprecated
- Features that will be removed in upcoming releases

### Removed
- Features that have been removed

### Fixed
- Bug fixes

### Security
- Security patches

## [1.0.0] - 2025-11-04

### Added
- Initial release
- REST API endpoints for session management, tools, and analytics
- WebSocket API for real-time communication
- Tool synthesis via TDD pipeline
- Semantic tool search
- Multi-tool workflow execution
- Conversational memory
- Workflow pattern learning
```

---

## Communication Channels

Deprecation notices and version updates are communicated through:

1. **Documentation**: Updated immediately with deprecation notices
2. **API Responses**: Deprecation headers and metadata
3. **Release Notes**: Detailed in GitHub releases
4. **Migration Guides**: Published for major version changes
5. **Email Notifications**: For registered API users (future)
6. **Status Page**: API status and planned deprecations (future)

---

## Best Practices for API Consumers

### 1. Version Pinning

Always specify the API version you're using:

```python
# Good
response = requests.get(
    'http://localhost:5001/api/v1/tools',
    headers={'X-API-Version': '1.0'}
)

# Bad (relies on default version)
response = requests.get('http://localhost:5001/api/tools')
```

### 2. Monitor Deprecation Headers

Check for deprecation headers in responses:

```python
response = requests.get('http://localhost:5001/api/tools')

if 'X-API-Deprecated' in response.headers:
    print(f"Warning: This endpoint is deprecated")
    print(f"Sunset date: {response.headers.get('X-API-Sunset')}")
    print(f"More info: {response.headers.get('X-API-Deprecation-Info')}")
```

### 3. Handle Deprecation Events

Listen for deprecation warning events:

```javascript
socket.on('deprecation_warning', (data) => {
    console.warn(`Deprecation: ${data.message}`);
    console.warn(`Alternative: ${data.alternative}`);
    console.warn(`Sunset date: ${data.sunset_date}`);
});
```

### 4. Test Against Multiple Versions

Test your integration against both current and upcoming versions:

```python
def test_api_compatibility():
    # Test current version
    response_v1 = requests.get('http://localhost:5001/api/v1/tools')
    assert response_v1.status_code == 200
    
    # Test upcoming version
    response_v2 = requests.get('http://localhost:5001/api/v2/capabilities')
    assert response_v2.status_code == 200
```

### 5. Subscribe to Updates

Stay informed about API changes:

- Watch the GitHub repository for releases
- Subscribe to the changelog RSS feed (future)
- Join the developer mailing list (future)

---

## Summary

The Self-Engineering Agent Framework follows a clear versioning and deprecation policy:

- **Semantic Versioning**: MAJOR.MINOR.PATCH format
- **12-Month Deprecation Period**: Features remain functional for 12 months after deprecation
- **Clear Communication**: Multiple channels for deprecation notices
- **Backward Compatibility**: Support for previous versions during transition periods
- **Migration Guides**: Detailed instructions for major version upgrades

This policy ensures that API consumers have sufficient time to migrate to new versions while maintaining the flexibility to evolve the framework.

---

## Contact

For questions about versioning or deprecation:

- GitHub Issues: https://github.com/haider-toha/Self-Engineering-Agent-Framework/issues
- Documentation: https://github.com/haider-toha/Self-Engineering-Agent-Framework/docs
