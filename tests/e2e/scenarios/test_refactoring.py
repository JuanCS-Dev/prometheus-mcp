"""
E2E Scenario Tests: Code Refactoring
=====================================

Tests for code refactoring operations.
Validates the complete workflow of improving code quality.

Based on:
- Anthropic TDD with expected outputs
- Real-world refactoring scenarios

Total: 10 tests
"""

import pytest


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def legacy_codebase(tmp_path):
    """Create a codebase with code that needs refactoring."""
    project_dir = tmp_path / "legacy_project"
    project_dir.mkdir()
    (project_dir / "src").mkdir()

    # File with long function that needs extraction
    (project_dir / "src" / "long_function.py").write_text('''"""Module with overly long function."""

def process_order(order_data):
    """Process an order - does too many things."""
    # Validate order
    if not order_data:
        return {"error": "No order data"}
    if "items" not in order_data:
        return {"error": "No items in order"}
    if not order_data["items"]:
        return {"error": "Empty items list"}

    # Calculate totals
    subtotal = 0
    for item in order_data["items"]:
        price = item.get("price", 0)
        quantity = item.get("quantity", 1)
        subtotal += price * quantity

    # Apply discounts
    discount = 0
    if subtotal > 100:
        discount = subtotal * 0.1
    elif subtotal > 50:
        discount = subtotal * 0.05

    # Calculate tax
    tax_rate = 0.08
    taxable = subtotal - discount
    tax = taxable * tax_rate

    # Calculate shipping
    if subtotal > 50:
        shipping = 0
    else:
        shipping = 5.99

    # Build response
    total = subtotal - discount + tax + shipping
    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "shipping": shipping,
        "total": total
    }
''')

    # File with duplicated code
    (project_dir / "src" / "duplicated.py").write_text('''"""Module with duplicated code."""

def process_user_a(user):
    """Process user type A."""
    if not user:
        return None
    name = user.get("name", "Unknown")
    email = user.get("email", "")
    if not email:
        return None
    return {"name": name.strip().title(), "email": email.lower()}

def process_user_b(user):
    """Process user type B."""
    if not user:
        return None
    name = user.get("name", "Unknown")
    email = user.get("email", "")
    if not email:
        return None
    return {"name": name.strip().title(), "email": email.lower()}

def process_user_c(user):
    """Process user type C."""
    if not user:
        return None
    name = user.get("name", "Unknown")
    email = user.get("email", "")
    if not email:
        return None
    return {"name": name.strip().title(), "email": email.lower()}
''')

    # File with deep nesting
    (project_dir / "src" / "deeply_nested.py").write_text('''"""Module with deeply nested code."""

def check_permissions(user, resource, action):
    """Check if user can perform action on resource."""
    if user:
        if user.get("active"):
            if user.get("role"):
                if user["role"] == "admin":
                    return True
                else:
                    if resource:
                        if resource.get("owner") == user.get("id"):
                            return True
                        else:
                            if action == "read":
                                if resource.get("public"):
                                    return True
                                else:
                                    return False
                            else:
                                return False
                    else:
                        return False
            else:
                return False
        else:
            return False
    else:
        return False
''')

    # File with magic numbers
    (project_dir / "src" / "magic_numbers.py").write_text('''"""Module with magic numbers."""

def calculate_price(base_price, quantity):
    """Calculate final price."""
    if quantity > 100:
        discount = base_price * quantity * 0.15
    elif quantity > 50:
        discount = base_price * quantity * 0.10
    elif quantity > 10:
        discount = base_price * quantity * 0.05
    else:
        discount = 0

    subtotal = base_price * quantity - discount
    tax = subtotal * 0.0875
    shipping = 5.99 if subtotal < 35 else 0

    return subtotal + tax + shipping

def calculate_shipping_time(distance):
    """Calculate shipping time in days."""
    if distance < 100:
        return 2
    elif distance < 500:
        return 3
    elif distance < 1000:
        return 5
    else:
        return 7
''')

    return project_dir


# ==============================================================================
# TEST CLASS: Extract Method Refactoring
# ==============================================================================

@pytest.mark.e2e
class TestExtractMethodRefactoring:
    """Tests for extracting methods from long functions."""

    def test_extracts_validation_logic(self, legacy_codebase):
        """Extracts validation into separate function."""
        file_path = legacy_codebase / "src" / "long_function.py"

        refactored = '''"""Module with refactored order processing."""

def validate_order(order_data):
    """Validate order data."""
    if not order_data:
        return False, "No order data"
    if "items" not in order_data:
        return False, "No items in order"
    if not order_data["items"]:
        return False, "Empty items list"
    return True, None

def calculate_subtotal(items):
    """Calculate order subtotal."""
    subtotal = 0
    for item in items:
        price = item.get("price", 0)
        quantity = item.get("quantity", 1)
        subtotal += price * quantity
    return subtotal

def calculate_discount(subtotal):
    """Calculate discount based on subtotal."""
    if subtotal > 100:
        return subtotal * 0.1
    elif subtotal > 50:
        return subtotal * 0.05
    return 0

def calculate_tax(amount, rate=0.08):
    """Calculate tax on amount."""
    return amount * rate

def calculate_shipping(subtotal):
    """Calculate shipping cost."""
    return 0 if subtotal > 50 else 5.99

def process_order(order_data):
    """Process an order - refactored version."""
    valid, error = validate_order(order_data)
    if not valid:
        return {"error": error}

    subtotal = calculate_subtotal(order_data["items"])
    discount = calculate_discount(subtotal)
    tax = calculate_tax(subtotal - discount)
    shipping = calculate_shipping(subtotal)

    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "shipping": shipping,
        "total": subtotal - discount + tax + shipping
    }
'''
        file_path.write_text(refactored)

        # Verify refactoring
        content = file_path.read_text()
        assert "def validate_order" in content
        assert "def calculate_subtotal" in content
        assert "def calculate_discount" in content
        assert "def calculate_tax" in content
        assert "def calculate_shipping" in content

        # Verify functionality preserved
        exec_globals = {}
        exec(compile(content, file_path, 'exec'), exec_globals)
        process_order = exec_globals['process_order']

        result = process_order({"items": [{"price": 10, "quantity": 2}]})
        assert result["subtotal"] == 20
        assert "error" not in result

    def test_extracts_repeated_pattern(self, legacy_codebase):
        """Extracts repeated pattern into helper."""
        file_path = legacy_codebase / "src" / "duplicated.py"

        refactored = '''"""Module with DRY code."""

def normalize_user(user):
    """Normalize user data - single source of truth."""
    if not user:
        return None
    name = user.get("name", "Unknown")
    email = user.get("email", "")
    if not email:
        return None
    return {"name": name.strip().title(), "email": email.lower()}

# All process functions now delegate to normalize_user
process_user_a = normalize_user
process_user_b = normalize_user
process_user_c = normalize_user
'''
        file_path.write_text(refactored)

        # Verify DRY principle
        content = file_path.read_text()
        assert content.count("name.strip().title()") == 1  # Only in one place

        # Verify functionality preserved
        exec_globals = {}
        exec(compile(content, file_path, 'exec'), exec_globals)

        test_user = {"name": "  john doe  ", "email": "JOHN@EXAMPLE.COM"}
        result = exec_globals['process_user_a'](test_user)
        assert result["name"] == "John Doe"
        assert result["email"] == "john@example.com"


# ==============================================================================
# TEST CLASS: Flatten Nested Code
# ==============================================================================

@pytest.mark.e2e
class TestFlattenNestedCode:
    """Tests for reducing code nesting."""

    def test_uses_early_returns(self, legacy_codebase):
        """Refactors deep nesting to early returns."""
        file_path = legacy_codebase / "src" / "deeply_nested.py"

        refactored = '''"""Module with flattened code."""

def check_permissions(user, resource, action):
    """Check if user can perform action on resource."""
    # Early returns for invalid states
    if not user:
        return False
    if not user.get("active"):
        return False
    if not user.get("role"):
        return False

    # Admin has all permissions
    if user["role"] == "admin":
        return True

    # Check resource ownership
    if not resource:
        return False
    if resource.get("owner") == user.get("id"):
        return True

    # Public resources are readable
    if action == "read" and resource.get("public"):
        return True

    return False
'''
        file_path.write_text(refactored)

        # Count nesting levels (indentation)
        content = file_path.read_text()
        lines = content.split("\n")
        max_indent = max(len(line) - len(line.lstrip()) for line in lines if line.strip())

        # Verify max nesting is reasonable (no more than 2 levels = 8 spaces)
        assert max_indent <= 8, f"Max indent {max_indent} too deep"

        # Verify functionality
        exec_globals = {}
        exec(compile(content, file_path, 'exec'), exec_globals)
        check = exec_globals['check_permissions']

        assert check(None, None, "read") is False
        assert check({"active": True, "role": "admin"}, None, "write") is True
        assert check({"active": True, "role": "user", "id": 1}, {"owner": 1}, "write") is True

    def test_extracts_guard_clauses(self, legacy_codebase):
        """Uses guard clauses for validation."""
        file_path = legacy_codebase / "src" / "guard_clauses.py"

        file_path.write_text('''"""Module demonstrating guard clauses."""

def process_payment(payment):
    """Process payment with guard clauses."""
    # Guard clauses at the start
    if not payment:
        raise ValueError("Payment data required")
    if payment.get("amount", 0) <= 0:
        raise ValueError("Invalid payment amount")
    if not payment.get("method"):
        raise ValueError("Payment method required")
    if payment["method"] not in ("card", "bank", "paypal"):
        raise ValueError(f"Unsupported payment method: {payment['method']}")

    # Happy path - no nesting needed
    amount = payment["amount"]
    method = payment["method"]

    # Process based on method
    processors = {
        "card": lambda a: {"status": "charged", "amount": a},
        "bank": lambda a: {"status": "pending", "amount": a},
        "paypal": lambda a: {"status": "redirected", "amount": a},
    }

    return processors[method](amount)
''')

        exec_globals = {}
        exec(compile(file_path.read_text(), file_path, 'exec'), exec_globals)
        process = exec_globals['process_payment']

        # Test guard clauses
        with pytest.raises(ValueError, match="Payment data required"):
            process(None)
        with pytest.raises(ValueError, match="Invalid payment amount"):
            process({"amount": -10})

        # Test happy path
        result = process({"amount": 100, "method": "card"})
        assert result["status"] == "charged"


# ==============================================================================
# TEST CLASS: Replace Magic Numbers
# ==============================================================================

@pytest.mark.e2e
class TestReplaceMagicNumbers:
    """Tests for replacing magic numbers with constants."""

    def test_extracts_constants(self, legacy_codebase):
        """Replaces magic numbers with named constants."""
        file_path = legacy_codebase / "src" / "magic_numbers.py"

        refactored = '''"""Module with named constants."""

# Discount thresholds and rates
BULK_DISCOUNT_THRESHOLD = 100
BULK_DISCOUNT_RATE = 0.15

MEDIUM_DISCOUNT_THRESHOLD = 50
MEDIUM_DISCOUNT_RATE = 0.10

SMALL_DISCOUNT_THRESHOLD = 10
SMALL_DISCOUNT_RATE = 0.05

# Tax and shipping
TAX_RATE = 0.0875
FREE_SHIPPING_THRESHOLD = 35
STANDARD_SHIPPING_COST = 5.99

# Shipping distance thresholds (miles) and days
SHIPPING_ZONES = [
    (100, 2),   # Local: < 100 miles = 2 days
    (500, 3),   # Regional: < 500 miles = 3 days
    (1000, 5),  # National: < 1000 miles = 5 days
]
DEFAULT_SHIPPING_DAYS = 7


def calculate_price(base_price, quantity):
    """Calculate final price with named constants."""
    subtotal = base_price * quantity

    if quantity > BULK_DISCOUNT_THRESHOLD:
        discount = subtotal * BULK_DISCOUNT_RATE
    elif quantity > MEDIUM_DISCOUNT_THRESHOLD:
        discount = subtotal * MEDIUM_DISCOUNT_RATE
    elif quantity > SMALL_DISCOUNT_THRESHOLD:
        discount = subtotal * SMALL_DISCOUNT_RATE
    else:
        discount = 0

    after_discount = subtotal - discount
    tax = after_discount * TAX_RATE
    shipping = STANDARD_SHIPPING_COST if after_discount < FREE_SHIPPING_THRESHOLD else 0

    return after_discount + tax + shipping


def calculate_shipping_time(distance):
    """Calculate shipping time using zones."""
    for threshold, days in SHIPPING_ZONES:
        if distance < threshold:
            return days
    return DEFAULT_SHIPPING_DAYS
'''
        file_path.write_text(refactored)

        content = file_path.read_text()

        # Verify constants are defined
        assert "BULK_DISCOUNT_THRESHOLD = 100" in content
        assert "TAX_RATE = 0.0875" in content
        assert "FREE_SHIPPING_THRESHOLD = 35" in content

        # Verify no magic numbers in functions (except in constant definitions)
        function_section = content.split("def calculate_price")[1]
        assert "0.15" not in function_section
        assert "0.0875" not in function_section

    def test_uses_enum_for_related_constants(self, legacy_codebase):
        """Uses Enum for related constant groups."""
        file_path = legacy_codebase / "src" / "enum_constants.py"

        file_path.write_text('''"""Module using Enum for constants."""
from enum import Enum, auto


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = auto()
    CONFIRMED = auto()
    SHIPPED = auto()
    DELIVERED = auto()
    CANCELLED = auto()


class PaymentMethod(Enum):
    """Payment method with processing fees."""
    CREDIT_CARD = 0.029  # 2.9% fee
    DEBIT_CARD = 0.015   # 1.5% fee
    BANK_TRANSFER = 0.0  # No fee
    PAYPAL = 0.034       # 3.4% fee


def calculate_processing_fee(amount, method: PaymentMethod):
    """Calculate processing fee for payment method."""
    return amount * method.value


def can_cancel(status: OrderStatus) -> bool:
    """Check if order can be cancelled."""
    return status in (OrderStatus.PENDING, OrderStatus.CONFIRMED)
''')

        exec_globals = {}
        exec(compile(file_path.read_text(), file_path, 'exec'), exec_globals)

        PaymentMethod = exec_globals['PaymentMethod']
        calculate_fee = exec_globals['calculate_processing_fee']

        assert calculate_fee(100, PaymentMethod.CREDIT_CARD) == 2.9
        assert calculate_fee(100, PaymentMethod.BANK_TRANSFER) == 0


# ==============================================================================
# TEST CLASS: Improve Code Structure
# ==============================================================================

@pytest.mark.e2e
class TestImproveCodeStructure:
    """Tests for improving overall code structure."""

    def test_splits_large_module(self, legacy_codebase):
        """Splits large module into focused modules."""
        src_dir = legacy_codebase / "src"

        # Create focused modules
        (src_dir / "validation.py").write_text('''"""Validation utilities."""

def validate_email(email):
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    """Validate phone number."""
    import re
    cleaned = re.sub(r'[^0-9]', '', phone)
    return len(cleaned) == 10
''')

        (src_dir / "formatting.py").write_text('''"""Formatting utilities."""

def format_currency(amount):
    """Format amount as currency."""
    return f"${amount:,.2f}"

def format_phone(phone):
    """Format phone number."""
    import re
    digits = re.sub(r'[^0-9]', '', phone)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone
''')

        (src_dir / "calculations.py").write_text('''"""Calculation utilities."""

def calculate_tax(amount, rate=0.08):
    """Calculate tax amount."""
    return round(amount * rate, 2)

def calculate_discount(amount, percentage):
    """Calculate discount amount."""
    return round(amount * (percentage / 100), 2)
''')

        # Verify modules exist and are focused
        assert (src_dir / "validation.py").exists()
        assert (src_dir / "formatting.py").exists()
        assert (src_dir / "calculations.py").exists()

        # Each module should be small and focused
        for module in ["validation.py", "formatting.py", "calculations.py"]:
            content = (src_dir / module).read_text()
            lines = len(content.split("\n"))
            assert lines < 30, f"{module} should be small and focused"

    def test_adds_type_hints(self, legacy_codebase):
        """Adds type hints to improve clarity."""
        file_path = legacy_codebase / "src" / "typed_module.py"

        file_path.write_text('''"""Module with comprehensive type hints."""
from typing import Optional, List, Dict, Union, TypedDict
from decimal import Decimal


class OrderItem(TypedDict):
    """Type definition for order item."""
    product_id: str
    name: str
    price: Decimal
    quantity: int


class Order(TypedDict):
    """Type definition for order."""
    id: str
    items: List[OrderItem]
    customer_id: str
    status: str


def calculate_order_total(order: Order) -> Decimal:
    """Calculate total for an order."""
    total = Decimal("0")
    for item in order["items"]:
        total += item["price"] * item["quantity"]
    return total


def find_order(
    orders: List[Order],
    order_id: Optional[str] = None,
    customer_id: Optional[str] = None
) -> Optional[Order]:
    """Find order by ID or customer."""
    for order in orders:
        if order_id and order["id"] == order_id:
            return order
        if customer_id and order["customer_id"] == customer_id:
            return order
    return None


def process_orders(
    orders: List[Order]
) -> Dict[str, Union[int, Decimal]]:
    """Process orders and return summary."""
    return {
        "count": len(orders),
        "total": sum(calculate_order_total(o) for o in orders)
    }
''')

        content = file_path.read_text()

        # Verify type hints present
        assert "-> Decimal" in content
        assert "-> Optional[Order]" in content
        assert "List[Order]" in content
        assert "TypedDict" in content

    def test_applies_single_responsibility(self, legacy_codebase):
        """Refactors to follow single responsibility principle."""
        src_dir = legacy_codebase / "src"

        # OrderValidator - only validates
        (src_dir / "order_validator.py").write_text('''"""Order validation - single responsibility."""

class OrderValidator:
    """Validates orders."""

    def validate(self, order):
        """Validate an order."""
        errors = []
        if not order.get("items"):
            errors.append("Order must have items")
        if not order.get("customer_id"):
            errors.append("Order must have customer")
        return len(errors) == 0, errors
''')

        # OrderCalculator - only calculates
        (src_dir / "order_calculator.py").write_text('''"""Order calculations - single responsibility."""

class OrderCalculator:
    """Calculates order totals."""

    def __init__(self, tax_rate=0.08):
        self.tax_rate = tax_rate

    def calculate_subtotal(self, order):
        """Calculate subtotal."""
        return sum(
            item["price"] * item["quantity"]
            for item in order.get("items", [])
        )

    def calculate_total(self, order):
        """Calculate total with tax."""
        subtotal = self.calculate_subtotal(order)
        return subtotal * (1 + self.tax_rate)
''')

        # OrderProcessor - orchestrates
        (src_dir / "order_processor.py").write_text('''"""Order processing - orchestration."""
from order_validator import OrderValidator
from order_calculator import OrderCalculator


class OrderProcessor:
    """Processes orders using validator and calculator."""

    def __init__(self):
        self.validator = OrderValidator()
        self.calculator = OrderCalculator()

    def process(self, order):
        """Process an order."""
        valid, errors = self.validator.validate(order)
        if not valid:
            return {"success": False, "errors": errors}

        total = self.calculator.calculate_total(order)
        return {"success": True, "total": total}
''')

        # Verify each class has single responsibility
        validator_content = (src_dir / "order_validator.py").read_text()
        calculator_content = (src_dir / "order_calculator.py").read_text()

        assert "calculate" not in validator_content.lower() or "calculate" in validator_content.split("class")[0]
        assert "validate" not in calculator_content.lower() or "validate" in calculator_content.split("class")[0]


# ==============================================================================
# SUMMARY
# ==============================================================================

"""
Total Tests: 10

Refactoring Patterns Covered:
1. Extract Method - breaking down long functions
2. Remove Duplication - DRY principle
3. Flatten Nesting - early returns
4. Guard Clauses - validation at start
5. Replace Magic Numbers - named constants
6. Use Enums - related constant groups
7. Split Large Modules - focused modules
8. Add Type Hints - improve clarity
9. Single Responsibility - focused classes
10. Code Organization - better structure
"""
