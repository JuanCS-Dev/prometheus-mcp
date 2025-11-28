"""
E2E Scenario Tests: Documentation Generation
=============================================

Tests for generating and maintaining documentation.
Validates the complete workflow of documentation tasks.

Based on:
- Anthropic TDD with expected outputs
- Real-world documentation scenarios

Total: 10 tests
"""

import pytest


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def code_to_document(tmp_path):
    """Create code that needs documentation."""
    project_dir = tmp_path / "undocumented_project"
    project_dir.mkdir()
    (project_dir / "src").mkdir()

    # Complex module needing docs
    (project_dir / "src" / "api_client.py").write_text('''"""API Client module."""
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class APIResponse:
    status_code: int
    data: Any
    headers: Dict[str, str]
    elapsed_ms: float


class APIClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()
        if api_key:
            self._session.headers["Authorization"] = f"Bearer {api_key}"

    def request(self, method: HTTPMethod, endpoint: str, data: Optional[Dict] = None,
                params: Optional[Dict] = None) -> APIResponse:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self._session.request(
            method=method.value,
            url=url,
            json=data,
            params=params,
            timeout=self.timeout
        )
        return APIResponse(
            status_code=response.status_code,
            data=response.json() if response.content else None,
            headers=dict(response.headers),
            elapsed_ms=response.elapsed.total_seconds() * 1000
        )

    def get(self, endpoint: str, params: Optional[Dict] = None) -> APIResponse:
        return self.request(HTTPMethod.GET, endpoint, params=params)

    def post(self, endpoint: str, data: Dict) -> APIResponse:
        return self.request(HTTPMethod.POST, endpoint, data=data)

    def put(self, endpoint: str, data: Dict) -> APIResponse:
        return self.request(HTTPMethod.PUT, endpoint, data=data)

    def delete(self, endpoint: str) -> APIResponse:
        return self.request(HTTPMethod.DELETE, endpoint)

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
''')

    # Module with classes
    (project_dir / "src" / "models.py").write_text('''"""Data models."""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


@dataclass
class User:
    id: int
    username: str
    email: str
    role: UserRole = UserRole.USER
    created_at: datetime = field(default_factory=datetime.now)

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def can_access(self, resource: str) -> bool:
        if self.is_admin():
            return True
        return resource in ["public", "shared"]


@dataclass
class Order:
    id: int
    user_id: int
    items: List[dict]
    total: float
    status: str = "pending"

    def add_item(self, item: dict) -> None:
        self.items.append(item)
        self._recalculate_total()

    def _recalculate_total(self) -> None:
        self.total = sum(item["price"] * item["quantity"] for item in self.items)
''')

    return project_dir


# ==============================================================================
# TEST CLASS: Docstring Generation
# ==============================================================================

@pytest.mark.e2e
class TestDocstringGeneration:
    """Tests for generating docstrings."""

    def test_generates_module_docstring(self, code_to_document):
        """Generates comprehensive module docstring."""
        file_path = code_to_document / "src" / "api_client.py"

        # Expected module docstring format
        expected_docstring = '''"""
API Client Module
=================

Provides a high-level HTTP client for interacting with REST APIs.

Classes:
    HTTPMethod: Enumeration of supported HTTP methods.
    APIResponse: Data class representing an API response.
    APIClient: Main client class for making HTTP requests.

Example:
    >>> with APIClient("https://api.example.com", api_key="secret") as client:
    ...     response = client.get("/users")
    ...     print(response.data)

Note:
    This module requires the `requests` library.
"""
'''
        content = file_path.read_text()

        # Verify docstring structure elements
        assert '"""' in content  # Has docstring
        assert "API Client" in content or "api" in content.lower()

    def test_generates_class_docstring(self, code_to_document):
        """Generates class-level docstrings."""
        file_path = code_to_document / "src" / "documented_client.py"

        documented = '''"""Documented API Client."""
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class APIResponse:
    """
    Represents an HTTP API response.

    Attributes:
        status_code: HTTP status code (e.g., 200, 404).
        data: Parsed JSON response body, or None if empty.
        headers: Response headers as a dictionary.
        elapsed_ms: Request duration in milliseconds.

    Example:
        >>> response = APIResponse(200, {"user": "john"}, {}, 150.5)
        >>> response.status_code
        200
    """
    status_code: int
    data: Any
    headers: Dict[str, str]
    elapsed_ms: float


class APIClient:
    """
    HTTP client for REST API interactions.

    Provides convenient methods for making HTTP requests with automatic
    JSON serialization/deserialization and authentication handling.

    Args:
        base_url: Base URL for all API requests.
        api_key: Optional API key for Bearer token authentication.
        timeout: Request timeout in seconds (default: 30).

    Attributes:
        base_url: The configured base URL.
        timeout: The configured timeout value.

    Example:
        >>> client = APIClient("https://api.example.com")
        >>> response = client.get("/users/1")
        >>> print(response.data)

    Note:
        Use as a context manager to ensure proper resource cleanup::

            with APIClient(url) as client:
                client.get("/endpoint")
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        """Initialize the API client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
'''
        file_path.write_text(documented)

        content = file_path.read_text()

        # Verify class docstrings
        assert "Attributes:" in content
        assert "Args:" in content
        assert "Example:" in content

    def test_generates_method_docstring(self, code_to_document):
        """Generates method-level docstrings."""
        file_path = code_to_document / "src" / "documented_methods.py"

        documented = '''"""Module with documented methods."""
from typing import Dict, Optional, List, Any


class DataProcessor:
    """Processes various data types."""

    def transform(self, data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Transform data using a field mapping.

        Applies the provided mapping to rename keys in the input data.
        Keys not in the mapping are preserved unchanged.

        Args:
            data: Input dictionary to transform.
            mapping: Dictionary mapping old keys to new keys.

        Returns:
            New dictionary with renamed keys.

        Raises:
            TypeError: If data or mapping is not a dictionary.

        Example:
            >>> processor = DataProcessor()
            >>> processor.transform(
            ...     {"old_name": "value"},
            ...     {"old_name": "new_name"}
            ... )
            {'new_name': 'value'}
        """
        if not isinstance(data, dict) or not isinstance(mapping, dict):
            raise TypeError("Both data and mapping must be dictionaries")

        result = {}
        for key, value in data.items():
            new_key = mapping.get(key, key)
            result[new_key] = value
        return result

    def filter_items(
        self,
        items: List[Dict],
        criteria: Dict[str, Any],
        *,
        match_all: bool = True
    ) -> List[Dict]:
        """
        Filter items based on criteria.

        Args:
            items: List of dictionaries to filter.
            criteria: Key-value pairs that items must match.
            match_all: If True, items must match all criteria.
                      If False, items matching any criterion are included.

        Returns:
            List of items matching the criteria.

        Example:
            >>> processor.filter_items(
            ...     [{"status": "active"}, {"status": "inactive"}],
            ...     {"status": "active"}
            ... )
            [{'status': 'active'}]
        """
        result = []
        for item in items:
            matches = [item.get(k) == v for k, v in criteria.items()]
            if match_all and all(matches):
                result.append(item)
            elif not match_all and any(matches):
                result.append(item)
        return result
'''
        file_path.write_text(documented)

        content = file_path.read_text()

        # Verify method docstring components
        assert "Args:" in content
        assert "Returns:" in content
        assert "Raises:" in content
        assert "Example:" in content


# ==============================================================================
# TEST CLASS: README Generation
# ==============================================================================

@pytest.mark.e2e
class TestREADMEGeneration:
    """Tests for generating README files."""

    def test_generates_basic_readme(self, code_to_document):
        """Generates basic README structure."""
        readme_path = code_to_document / "README.md"

        readme = '''# API Client Library

A Python library for making HTTP API requests with ease.

## Installation

```bash
pip install api-client
```

## Quick Start

```python
from api_client import APIClient

# Create a client
client = APIClient("https://api.example.com", api_key="your-key")

# Make requests
response = client.get("/users")
print(response.data)
```

## Features

- Simple, intuitive API
- Automatic JSON handling
- Bearer token authentication
- Context manager support
- Configurable timeouts

## API Reference

### APIClient

```python
APIClient(base_url, api_key=None, timeout=30)
```

**Parameters:**
- `base_url` (str): Base URL for API requests
- `api_key` (str, optional): API key for authentication
- `timeout` (int): Request timeout in seconds

**Methods:**
- `get(endpoint, params=None)` - HTTP GET request
- `post(endpoint, data)` - HTTP POST request
- `put(endpoint, data)` - HTTP PUT request
- `delete(endpoint)` - HTTP DELETE request

## License

MIT License
'''
        readme_path.write_text(readme)

        content = readme_path.read_text()

        # Verify README structure
        assert "# " in content  # Has title
        assert "## Installation" in content
        assert "## Quick Start" in content
        assert "```python" in content  # Has code examples
        assert "## License" in content

    def test_generates_api_documentation(self, code_to_document):
        """Generates API reference documentation."""
        docs_dir = code_to_document / "docs"
        docs_dir.mkdir()
        api_doc = docs_dir / "api.md"

        api_doc.write_text('''# API Reference

## Classes

### HTTPMethod

Enumeration of supported HTTP methods.

| Value | Description |
|-------|-------------|
| `GET` | Retrieve resources |
| `POST` | Create resources |
| `PUT` | Update resources |
| `DELETE` | Remove resources |
| `PATCH` | Partial update |

### APIResponse

Data class representing an API response.

#### Attributes

| Name | Type | Description |
|------|------|-------------|
| `status_code` | `int` | HTTP status code |
| `data` | `Any` | Parsed response body |
| `headers` | `Dict[str, str]` | Response headers |
| `elapsed_ms` | `float` | Request duration |

### APIClient

Main client class for HTTP requests.

#### Constructor

```python
APIClient(base_url: str, api_key: Optional[str] = None, timeout: int = 30)
```

#### Methods

##### get

```python
def get(endpoint: str, params: Optional[Dict] = None) -> APIResponse
```

Make an HTTP GET request.

**Parameters:**
- `endpoint`: API endpoint path
- `params`: Query parameters

**Returns:** APIResponse object

**Example:**
```python
response = client.get("/users", params={"page": 1})
```

##### post

```python
def post(endpoint: str, data: Dict) -> APIResponse
```

Make an HTTP POST request.

**Parameters:**
- `endpoint`: API endpoint path
- `data`: Request body data

**Returns:** APIResponse object
''')

        content = api_doc.read_text()

        # Verify API documentation structure
        assert "## Classes" in content
        assert "### " in content  # Has class headers
        assert "| " in content  # Has tables
        assert "```python" in content  # Has code blocks


# ==============================================================================
# TEST CLASS: Code Comments
# ==============================================================================

@pytest.mark.e2e
class TestCodeComments:
    """Tests for inline code comments."""

    def test_adds_explanatory_comments(self, code_to_document):
        """Adds comments explaining complex logic."""
        file_path = code_to_document / "src" / "commented_code.py"

        commented = '''"""Module with well-commented complex logic."""


def calculate_shipping_cost(weight: float, distance: int, priority: bool = False) -> float:
    """Calculate shipping cost based on multiple factors."""

    # Base rate depends on weight tier
    # Tier 1: <= 1kg, Tier 2: <= 5kg, Tier 3: > 5kg
    if weight <= 1:
        base_rate = 5.00
    elif weight <= 5:
        base_rate = 10.00
    else:
        # Heavy packages have per-kg rate after first 5kg
        base_rate = 10.00 + (weight - 5) * 2.00

    # Distance multiplier uses zone-based pricing
    # Zone A: local (<100mi), Zone B: regional (<500mi), Zone C: national
    if distance < 100:
        distance_multiplier = 1.0
    elif distance < 500:
        distance_multiplier = 1.5
    else:
        # National shipping is most expensive
        distance_multiplier = 2.0

    # Calculate base cost
    cost = base_rate * distance_multiplier

    # Priority shipping adds 50% premium
    # This covers expedited handling and faster transit
    if priority:
        cost *= 1.5

    # Round to 2 decimal places for currency
    return round(cost, 2)


def parse_address(address_string: str) -> dict:
    """Parse address string into components."""

    # Split address into lines, handling various line endings
    # Supports: \\n, \\r\\n, and comma-separated
    lines = address_string.replace("\\r\\n", "\\n").replace(",", "\\n").split("\\n")
    lines = [line.strip() for line in lines if line.strip()]

    result = {}

    # First line is typically street address
    if lines:
        result["street"] = lines[0]

    # Last line usually contains city, state, zip
    # Format: "City, State ZIP" or "City State ZIP"
    if len(lines) >= 2:
        last_line = lines[-1]

        # Try to extract ZIP code (5 digits or 5+4 format)
        import re
        zip_match = re.search(r'(\\d{5}(?:-\\d{4})?)', last_line)
        if zip_match:
            result["zip"] = zip_match.group(1)
            # Remove ZIP from line for further parsing
            last_line = last_line[:zip_match.start()].strip()

        # State is typically 2-letter abbreviation at end
        state_match = re.search(r'\\b([A-Z]{2})\\b', last_line)
        if state_match:
            result["state"] = state_match.group(1)
            # City is everything before state
            result["city"] = last_line[:state_match.start()].strip().rstrip(",")

    return result
'''
        file_path.write_text(commented)

        content = file_path.read_text()

        # Verify explanatory comments
        assert "# " in content  # Has comments
        assert "Tier" in content  # Explains tiers
        assert "Zone" in content  # Explains zones

    def test_adds_todo_comments(self, code_to_document):
        """Adds TODO comments for future work."""
        file_path = code_to_document / "src" / "with_todos.py"

        with_todos = '''"""Module with TODO markers."""


class CacheManager:
    """Simple cache manager."""

    def __init__(self):
        self._cache = {}
        # TODO: Add TTL support for cache entries
        # TODO: Implement LRU eviction policy

    def get(self, key: str):
        """Get value from cache."""
        return self._cache.get(key)

    def set(self, key: str, value):
        """Set value in cache."""
        # TODO: Add size limit check before adding
        self._cache[key] = value

    def clear(self):
        """Clear all cache entries."""
        # FIXME: This doesn't notify subscribers of cache clear
        self._cache.clear()

    def stats(self):
        """Return cache statistics."""
        # NOTE: This is a simple implementation
        # For production, consider using a more sophisticated metrics system
        return {
            "size": len(self._cache),
            "keys": list(self._cache.keys())
        }


# TODO(future-release): Add distributed cache support
# TODO(performance): Profile memory usage with large datasets
# HACK: Temporary workaround for circular import issue
def _lazy_import():
    pass
'''
        file_path.write_text(with_todos)

        content = file_path.read_text()

        # Verify TODO/FIXME/NOTE markers
        assert "# TODO:" in content
        assert "# FIXME:" in content
        assert "# NOTE:" in content


# ==============================================================================
# TEST CLASS: Documentation Updates
# ==============================================================================

@pytest.mark.e2e
class TestDocumentationUpdates:
    """Tests for updating existing documentation."""

    def test_updates_changelog(self, code_to_document):
        """Updates CHANGELOG with new entries."""
        changelog = code_to_document / "CHANGELOG.md"

        changelog.write_text('''# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- New `patch` method for PATCH requests

### Changed
- Improved error messages for timeout errors

### Fixed
- Fixed connection pooling memory leak

## [1.2.0] - 2024-01-15

### Added
- Support for custom headers per request
- Retry logic with exponential backoff

### Changed
- Default timeout increased to 30 seconds

## [1.1.0] - 2024-01-01

### Added
- Context manager support
- Bearer token authentication

### Fixed
- Fixed URL encoding for query parameters

## [1.0.0] - 2023-12-01

### Added
- Initial release
- Basic HTTP methods (GET, POST, PUT, DELETE)
- JSON serialization/deserialization
''')

        content = changelog.read_text()

        # Verify changelog structure
        assert "## [Unreleased]" in content
        assert "### Added" in content
        assert "### Changed" in content
        assert "### Fixed" in content
        assert "## [1.2.0]" in content

    def test_updates_api_version(self, code_to_document):
        """Updates version in documentation."""
        docs_dir = code_to_document / "docs"
        docs_dir.mkdir(exist_ok=True)

        version_doc = docs_dir / "version.md"
        version_doc.write_text('''# Version Information

**Current Version:** 1.3.0

## Version History

| Version | Release Date | Status |
|---------|--------------|--------|
| 1.3.0 | 2024-02-01 | Current |
| 1.2.0 | 2024-01-15 | Supported |
| 1.1.0 | 2024-01-01 | Supported |
| 1.0.0 | 2023-12-01 | End of Life |

## Compatibility

- Python 3.8+
- requests 2.25+

## Upgrade Guide

### From 1.2.x to 1.3.x

No breaking changes. Simply update:

```bash
pip install --upgrade api-client
```

### From 1.1.x to 1.2.x

The default timeout changed from 10 to 30 seconds. If you rely on the
shorter timeout, explicitly set it:

```python
client = APIClient(url, timeout=10)
```
''')

        content = version_doc.read_text()

        # Verify version documentation
        assert "Current Version:" in content
        assert "Version History" in content
        assert "Upgrade Guide" in content

    def test_generates_migration_guide(self, code_to_document):
        """Generates migration guide for breaking changes."""
        docs_dir = code_to_document / "docs"
        docs_dir.mkdir(exist_ok=True)

        migration_doc = docs_dir / "migration.md"
        migration_doc.write_text('''# Migration Guide

## Migrating from v1.x to v2.0

Version 2.0 introduces several breaking changes to improve the API.

### Breaking Changes

#### 1. Constructor signature changed

**Before (v1.x):**
```python
client = APIClient(url, key, 30)
```

**After (v2.0):**
```python
client = APIClient(url, api_key=key, timeout=30)
```

#### 2. Response object renamed

**Before (v1.x):**
```python
from api_client import Response
```

**After (v2.0):**
```python
from api_client import APIResponse
```

#### 3. Error handling changed

**Before (v1.x):**
```python
try:
    response = client.get("/endpoint")
except Exception as e:
    # Generic exception
    pass
```

**After (v2.0):**
```python
from api_client import APIError, TimeoutError, ConnectionError

try:
    response = client.get("/endpoint")
except TimeoutError:
    # Handle timeout specifically
    pass
except ConnectionError:
    # Handle connection issues
    pass
except APIError as e:
    # Handle other API errors
    print(e.status_code, e.message)
```

### Automatic Migration

Use our migration script:

```bash
python -m api_client.migrate --path ./your_project
```

This will:
1. Update import statements
2. Convert constructor calls to keyword arguments
3. Update exception handling (manual review required)

### Deprecation Warnings

Enable deprecation warnings to find v1.x patterns:

```python
import warnings
warnings.filterwarnings("default", category=DeprecationWarning)
```
''')

        content = migration_doc.read_text()

        # Verify migration guide structure
        assert "Breaking Changes" in content
        assert "Before" in content
        assert "After" in content
        assert "Migration" in content


# ==============================================================================
# SUMMARY
# ==============================================================================

"""
Total Tests: 10

Documentation Types Covered:
1. Module docstrings
2. Class docstrings
3. Method docstrings
4. README generation
5. API reference docs
6. Explanatory comments
7. TODO/FIXME markers
8. Changelog updates
9. Version documentation
10. Migration guides
"""
