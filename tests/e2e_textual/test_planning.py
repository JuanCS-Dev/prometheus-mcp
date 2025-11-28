"""E2E Tests: Planning Mode Workflows.

Tests the planning and architecture capabilities.
"""

import pytest
import time

from .conftest import TestResult


class TestPlanningMode:
    """Test planning mode functionality."""

    @pytest.mark.asyncio
    async def test_enter_and_exit_plan_mode(self, temp_project, e2e_report):
        """Test entering and exiting plan mode."""
        start_time = time.time()
        result = TestResult(
            name="enter_exit_plan_mode",
            status="passed",
            duration=0.0,
            metadata={"test_type": "plan_mode_lifecycle"}
        )

        try:
            from jdev_cli.tools.plan_mode import (
                EnterPlanModeTool,
                ExitPlanModeTool,
                get_plan_state,
                reset_plan_state
            )

            reset_plan_state()

            enter_tool = EnterPlanModeTool()
            exit_tool = ExitPlanModeTool()

            # Enter plan mode
            plan_file = temp_project / ".jdev" / "plans" / "test_plan.md"
            enter_result = await enter_tool._execute_validated(
                task_description="Implement user authentication system",
                plan_file=str(plan_file)
            )

            assert enter_result.success, f"Failed to enter plan mode: {enter_result.error}"
            assert get_plan_state().active is True
            assert plan_file.exists()
            result.logs.append("✓ Entered plan mode")
            result.logs.append(f"✓ Created plan file: {plan_file.name}")

            # Write to plan
            plan_content = plan_file.read_text()
            plan_content += """

## Implementation Plan

### Phase 1: Setup
- Create User model
- Setup database migrations
- Configure authentication middleware

### Phase 2: Core Features
- Implement registration endpoint
- Implement login endpoint
- Add password hashing
- Generate JWT tokens

### Phase 3: Security
- Add rate limiting
- Implement refresh tokens
- Add audit logging

### Phase 4: Testing
- Unit tests for auth service
- Integration tests for endpoints
- Security testing

## Estimated Complexity: Medium
## Dependencies: FastAPI, SQLAlchemy, python-jose, passlib
"""
            plan_file.write_text(plan_content)
            result.logs.append("✓ Wrote implementation plan")

            # Exit plan mode
            exit_result = await exit_tool._execute_validated(
                summary="Authentication system implementation plan"
            )

            assert exit_result.success, f"Failed to exit plan mode: {exit_result.error}"
            assert exit_result.data["status"] == "plan_submitted"
            result.logs.append("✓ Exited plan mode")

            result.metadata["plan_file"] = str(plan_file)
            result.metadata["plan_size"] = len(plan_content)

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_create_architecture_plan(self, temp_project, e2e_report):
        """Test creating a detailed architecture plan."""
        start_time = time.time()
        result = TestResult(
            name="create_architecture_plan",
            status="passed",
            duration=0.0,
            metadata={"test_type": "architecture"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool

            write_tool = WriteFileTool()

            # Create architecture document
            arch_content = """# Architecture Plan: E-Commerce Platform

## Overview

This document outlines the architecture for a modern e-commerce platform.

## System Components

### 1. Frontend (React + TypeScript)
```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   ├── products/
│   │   ├── cart/
│   │   └── checkout/
│   ├── hooks/
│   ├── services/
│   ├── store/
│   └── utils/
├── tests/
└── package.json
```

### 2. Backend API (FastAPI)
```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── products.py
│   │   │   ├── orders.py
│   │   │   ├── users.py
│   │   │   └── payments.py
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── events.py
│   ├── models/
│   ├── schemas/
│   └── services/
├── tests/
└── requirements.txt
```

### 3. Database (PostgreSQL)
- Products table
- Users table
- Orders table
- Order items table
- Payments table
- Inventory table

### 4. Cache (Redis)
- Session storage
- Product catalog cache
- Rate limiting
- Shopping cart (temporary)

### 5. Message Queue (RabbitMQ)
- Order processing
- Email notifications
- Inventory updates

## Data Flow

```
[Client] --> [Load Balancer] --> [API Gateway]
                                      |
                    +-----------------+-----------------+
                    |                 |                 |
                [Product API]    [Order API]      [User API]
                    |                 |                 |
                    +--------+--------+--------+--------+
                             |                 |
                        [PostgreSQL]       [Redis]
                             |
                        [RabbitMQ]
                             |
                    +--------+--------+
                    |                 |
            [Email Service]   [Inventory Service]
```

## Security Considerations

1. **Authentication**: JWT tokens with refresh
2. **Authorization**: Role-based access control
3. **Data Protection**: Encryption at rest and in transit
4. **Input Validation**: Pydantic schemas
5. **Rate Limiting**: Per-user and per-endpoint

## Scalability

- Horizontal scaling via Kubernetes
- Database read replicas
- CDN for static assets
- Microservices decomposition ready

## Monitoring

- Prometheus metrics
- Grafana dashboards
- ELK stack for logging
- Sentry for error tracking

---
Generated by Juan-Dev-Code Planning Mode
"""
            (temp_project / "docs").mkdir(exist_ok=True)
            write_result = await write_tool._execute_validated(
                path=str(temp_project / "docs" / "ARCHITECTURE.md"),
                content=arch_content
            )

            assert write_result.success
            result.logs.append("✓ Created architecture document")
            result.metadata["sections"] = [
                "Overview", "System Components", "Data Flow",
                "Security", "Scalability", "Monitoring"
            ]
            result.metadata["components"] = 5

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_create_implementation_checklist(self, temp_project, e2e_report):
        """Test creating an implementation checklist."""
        start_time = time.time()
        result = TestResult(
            name="create_implementation_checklist",
            status="passed",
            duration=0.0,
            metadata={"test_type": "checklist"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool

            write_tool = WriteFileTool()

            checklist = """# Implementation Checklist

## Phase 1: Project Setup ✅
- [x] Initialize git repository
- [x] Create project structure
- [x] Setup virtual environment
- [x] Install dependencies
- [x] Configure linting (ruff)
- [x] Configure formatting (black)
- [x] Setup pre-commit hooks

## Phase 2: Core Models 🚧
- [x] User model
- [x] Product model
- [ ] Order model
- [ ] Payment model
- [ ] Inventory model

## Phase 3: API Endpoints 📝
- [x] GET /products
- [x] GET /products/{id}
- [ ] POST /products (admin)
- [ ] PUT /products/{id} (admin)
- [ ] DELETE /products/{id} (admin)
- [ ] GET /orders
- [ ] POST /orders
- [ ] GET /orders/{id}

## Phase 4: Authentication 🔐
- [ ] User registration
- [ ] User login
- [ ] Password reset
- [ ] Email verification
- [ ] JWT token generation
- [ ] Token refresh

## Phase 5: Testing 🧪
- [ ] Unit tests (80% coverage)
- [ ] Integration tests
- [ ] E2E tests
- [ ] Load testing
- [ ] Security testing

## Phase 6: Documentation 📚
- [ ] API documentation (OpenAPI)
- [ ] README
- [ ] Contributing guide
- [ ] Deployment guide

## Phase 7: Deployment 🚀
- [ ] Docker setup
- [ ] CI/CD pipeline
- [ ] Staging environment
- [ ] Production deployment
- [ ] Monitoring setup

---
Progress: 12/35 tasks (34%)
Last updated: 2024-01-15
"""
            write_result = await write_tool._execute_validated(
                path=str(temp_project / "CHECKLIST.md"),
                content=checklist
            )

            assert write_result.success
            result.logs.append("✓ Created implementation checklist")
            result.metadata["total_tasks"] = 35
            result.metadata["completed_tasks"] = 12
            result.metadata["phases"] = 7

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestArchitectAgent:
    """Test architect agent planning capabilities."""

    @pytest.mark.asyncio
    async def test_architect_analyzes_requirements(self, temp_project, e2e_report):
        """Test architect agent analyzing requirements."""
        start_time = time.time()
        result = TestResult(
            name="architect_analyzes_requirements",
            status="passed",
            duration=0.0,
            metadata={"agent": "architect"}
        )

        try:
            # Create requirements document
            requirements = """# Product Requirements

## User Stories

1. As a user, I want to browse products so I can find items to purchase
2. As a user, I want to add items to cart so I can buy multiple items
3. As a user, I want to checkout securely so I can complete my purchase
4. As an admin, I want to manage products so I can update the catalog

## Non-Functional Requirements

- Response time < 200ms for 95th percentile
- Support 1000 concurrent users
- 99.9% uptime SLA
- GDPR compliant data handling
"""
            req_file = temp_project / "REQUIREMENTS.md"
            req_file.write_text(requirements)

            # Simulate architect analysis
            from jdev_cli.tools.file_ops import ReadFileTool, WriteFileTool

            read_tool = ReadFileTool()
            write_tool = WriteFileTool()

            read_result = await read_tool._execute_validated(path=str(req_file))
            assert read_result.success

            # Generate analysis
            analysis = """# Requirements Analysis

## Functional Analysis

### User-Facing Features
| ID | Story | Complexity | Priority |
|----|-------|------------|----------|
| US-1 | Browse products | Low | P0 |
| US-2 | Add to cart | Medium | P0 |
| US-3 | Secure checkout | High | P0 |
| US-4 | Product management | Medium | P1 |

### Technical Requirements
- **Performance**: Need caching layer (Redis)
- **Scalability**: Horizontal scaling, load balancer
- **Security**: OAuth2, PCI DSS for payments
- **Compliance**: GDPR - data encryption, consent management

## Recommended Tech Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| Backend | FastAPI | Performance, async support |
| Database | PostgreSQL | ACID, reliability |
| Cache | Redis | Speed, sessions |
| Frontend | React | Component reuse |
| Payments | Stripe | PCI compliance |

## Risk Assessment

1. **High**: Payment integration complexity
2. **Medium**: Performance under load
3. **Low**: UI/UX implementation

## Estimated Timeline

- Phase 1 (Setup): 1 week
- Phase 2 (Core): 3 weeks
- Phase 3 (Payments): 2 weeks
- Phase 4 (Testing): 2 weeks
- **Total**: 8 weeks

---
Generated by Architect Agent
"""
            write_result = await write_tool._execute_validated(
                path=str(temp_project / "ANALYSIS.md"),
                content=analysis
            )

            assert write_result.success
            result.logs.append("✓ Read requirements document")
            result.logs.append("✓ Generated requirements analysis")
            result.logs.append("✓ Created tech stack recommendations")
            result.logs.append("✓ Produced timeline estimate")
            result.metadata["user_stories"] = 4
            result.metadata["estimated_weeks"] = 8

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error
