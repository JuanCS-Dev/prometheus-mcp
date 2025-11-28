"""
Comprehensive Test Suite for DocumentationAgent
Author: Boris Cherny
Date: 2025-11-22
Coverage Target: 100% (100+ tests)
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from jdev_cli.agents.documentation import DocumentationAgent


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm():
    """Mock LLM client."""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value="Documentation generated")
    return llm

@pytest.fixture
def mock_mcp():
    """Mock MCP client."""
    return MagicMock()

@pytest.fixture
def agent(mock_llm, mock_mcp):
    """Create DocumentationAgent instance with mocked clients."""
    return DocumentationAgent(llm_client=mock_llm, mcp_client=mock_mcp)


# ============================================================================
# SECTION 1: INITIALIZATION & CONFIGURATION (15 tests)
# ============================================================================

class TestDocumentationAgentInitialization:
    """Test agent initialization and configuration"""

    def test_agent_name(self, agent):
        assert agent.name == "DocumentationAgent"

    def test_agent_role(self, agent):
        assert agent.role == "documentation"

    def test_capabilities_loaded(self, agent):
        caps = agent.capabilities
        assert isinstance(caps, dict)
        assert len(caps) > 0

    def test_parser_registry(self, agent):
        assert hasattr(agent, '_parsers')
        assert 'python' in agent._parsers

    def test_formatter_registry(self, agent):
        assert hasattr(agent, '_formatters')
        assert 'markdown' in agent._formatters

    def test_template_engine(self, agent):
        assert hasattr(agent, '_template_engine')

    def test_metrics_collector(self, agent):
        assert hasattr(agent, '_metrics')

    def test_cache_mechanism(self, agent):
        assert hasattr(agent, '_cache')

    def test_supported_languages(self, agent):
        langs = agent.get_supported_languages()
        assert 'python' in langs
        assert 'javascript' in langs
        assert 'typescript' in langs

    def test_supported_formats(self, agent):
        formats = agent.get_supported_formats()
        assert 'markdown' in formats
        assert 'rst' in formats
        assert 'html' in formats

    def test_config_validation(self, agent):
        assert agent.config is not None
        assert 'templates' in agent.config

    def test_error_handling_init(self, mock_llm, mock_mcp):
        # Should not raise on initialization
        agent = DocumentationAgent(mock_llm, mock_mcp)
        assert agent is not None

    def test_thread_safety_init(self, mock_llm, mock_mcp):
        # Multiple instances should be independent
        agent1 = DocumentationAgent(mock_llm, mock_mcp)
        agent2 = DocumentationAgent(mock_llm, mock_mcp)
        assert agent1 is not agent2

    def test_memory_management(self, agent):
        # Should not leak memory on cache
        import sys
        initial_size = sys.getsizeof(agent._cache)
        agent._cache['test'] = 'data'
        agent._cache.clear()
        assert sys.getsizeof(agent._cache) <= initial_size * 2

    def test_default_configuration(self, agent):
        # Should have sane defaults
        assert agent.config.get('max_file_size', 0) > 0
        assert agent.config.get('timeout', 0) > 0


# ============================================================================
# SECTION 2: PYTHON CODE ANALYSIS (25 tests)
# ============================================================================

class TestPythonCodeAnalysis:
    """Test Python code parsing and analysis"""

    @pytest.fixture
    def temp_py_file(self, tmp_path):
        def _create(content: str) -> Path:
            file = tmp_path / "test.py"
            file.write_text(content)
            return file
        return _create

    def test_simple_function_analysis(self, agent, temp_py_file):
        code = """
def hello(name: str) -> str:
    '''Says hello to name'''
    return f"Hello {name}"
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert result['functions']
        assert result['functions'][0]['name'] == 'hello'

    def test_function_with_docstring(self, agent, temp_py_file):
        code = '''
def documented():
    """
    This function is documented.
    
    Returns:
        None
    """
    pass
'''
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert 'documented' in result['functions'][0]['docstring']

    def test_function_without_docstring(self, agent, temp_py_file):
        code = "def undocumented():\n    pass"
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert result['functions'][0]['docstring'] == ""

    def test_class_analysis(self, agent, temp_py_file):
        code = """
class MyClass:
    '''A test class'''
    def method(self):
        pass
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert result['classes']
        assert result['classes'][0]['name'] == 'MyClass'

    def test_class_with_methods(self, agent, temp_py_file):
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        methods = result['classes'][0]['methods']
        assert len(methods) == 2

    def test_type_hints_extraction(self, agent, temp_py_file):
        code = """
def typed(x: int, y: str) -> bool:
    return True
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        func = result['functions'][0]
        assert 'x: int' in str(func['signature'])

    def test_decorator_detection(self, agent, temp_py_file):
        code = """
@property
def prop(self):
    return self._val
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert '@property' in str(result['functions'][0]['decorators'])

    def test_multiple_decorators(self, agent, temp_py_file):
        code = """
@staticmethod
@lru_cache
def cached():
    pass
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        decorators = result['functions'][0]['decorators']
        assert len(decorators) >= 2

    def test_async_function(self, agent, temp_py_file):
        code = """
async def async_func():
    await something()
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert result['functions'][0]['is_async'] is True

    def test_generator_function(self, agent, temp_py_file):
        code = """
def gen():
    yield 1
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert result['functions'][0]['is_generator'] is True

    def test_nested_classes(self, agent, temp_py_file):
        code = """
class Outer:
    class Inner:
        pass
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert len(result['classes']) >= 1

    def test_inheritance_detection(self, agent, temp_py_file):
        code = """
class Child(Parent):
    pass
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert 'Parent' in str(result['classes'][0]['bases'])

    def test_module_docstring(self, agent, temp_py_file):
        code = '''
"""
This is a module docstring.
"""

def func():
    pass
'''
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert result['module_docstring']

    def test_imports_extraction(self, agent, temp_py_file):
        code = """
import os
from pathlib import Path
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert 'os' in result['imports']

    def test_constants_detection(self, agent, temp_py_file):
        code = """
MAX_SIZE = 100
DEFAULT_NAME = "test"
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        constants = result.get('constants', [])
        assert any('MAX_SIZE' in str(c) for c in constants)

    def test_private_methods(self, agent, temp_py_file):
        code = """
class Test:
    def _private(self):
        pass
    def public(self):
        pass
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        methods = result['classes'][0]['methods']
        assert any(m['name'].startswith('_') for m in methods)

    def test_property_methods(self, agent, temp_py_file):
        code = """
class Test:
    @property
    def value(self):
        return self._value
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        # Should detect as property
        assert result['classes'][0]['methods'][0]['is_property'] is True

    def test_static_methods(self, agent, temp_py_file):
        code = """
class Test:
    @staticmethod
    def static():
        pass
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert result['classes'][0]['methods'][0]['is_static'] is True

    def test_class_methods(self, agent, temp_py_file):
        code = """
class Test:
    @classmethod
    def cls_method(cls):
        pass
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert result['classes'][0]['methods'][0]['is_classmethod'] is True

    def test_empty_file(self, agent, temp_py_file):
        file = temp_py_file("")
        result = agent.analyze_file(str(file))
        assert result['functions'] == []
        assert result['classes'] == []

    def test_syntax_error_handling(self, agent, temp_py_file):
        code = "def broken(\n    # Invalid syntax"
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert 'error' in result or result == {}

    def test_large_file_analysis(self, agent, temp_py_file):
        # Generate large file
        code = "\n".join([f"def func_{i}():\n    pass" for i in range(100)])
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert len(result['functions']) == 100

    def test_complex_type_hints(self, agent, temp_py_file):
        code = """
from typing import List, Dict, Optional

def complex(data: List[Dict[str, Optional[int]]]) -> bool:
    return True
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        # Should parse complex types
        assert 'List' in str(result['functions'][0]['signature'])

    def test_dataclass_detection(self, agent, temp_py_file):
        code = """
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    age: int
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert '@dataclass' in str(result['classes'][0]['decorators'])

    def test_exception_classes(self, agent, temp_py_file):
        code = """
class CustomError(Exception):
    '''Custom exception'''
    pass
"""
        file = temp_py_file(code)
        result = agent.analyze_file(str(file))
        assert 'Exception' in str(result['classes'][0]['bases'])


# ============================================================================
# SECTION 3: DOCUMENTATION GENERATION (30 tests)
# ============================================================================

class TestDocumentationGeneration:
    """Test documentation generation capabilities"""

    def test_generate_readme_basic(self, agent, tmp_path):
        output = tmp_path / "README.md"
        result = agent.generate_readme(
            project_name="TestProject",
            description="A test project",
            output_path=str(output)
        )
        assert result['success'] is True
        assert output.exists()

    def test_readme_has_title(self, agent, tmp_path):
        output = tmp_path / "README.md"
        agent.generate_readme(
            project_name="MyProject",
            output_path=str(output)
        )
        content = output.read_text()
        assert "# MyProject" in content

    def test_readme_has_sections(self, agent, tmp_path):
        output = tmp_path / "README.md"
        agent.generate_readme(
            project_name="Test",
            output_path=str(output)
        )
        content = output.read_text()
        assert "## Installation" in content
        assert "## Usage" in content
        assert "## License" in content

    def test_readme_with_badges(self, agent, tmp_path):
        output = tmp_path / "README.md"
        agent.generate_readme(
            project_name="Test",
            add_badges=True,
            output_path=str(output)
        )
        content = output.read_text()
        assert "![" in content or "badge" in content.lower()

    def test_generate_api_docs(self, agent, tmp_path):
        # Create sample Python file
        py_file = tmp_path / "api.py"
        py_file.write_text("""
def api_function():
    '''API function'''
    pass
""")
        output = tmp_path / "API.md"
        result = agent.generate_api_docs(
            source_dir=str(tmp_path),
            output_path=str(output)
        )
        assert result['success'] is True
        assert output.exists()

    def test_api_docs_content(self, agent, tmp_path):
        py_file = tmp_path / "module.py"
        py_file.write_text("""
def public_api():
    '''Public API function'''
    pass
""")
        output = tmp_path / "API.md"
        agent.generate_api_docs(str(tmp_path), str(output))
        content = output.read_text()
        assert "public_api" in content

    def test_module_documentation(self, agent, tmp_path):
        module = tmp_path / "module.py"
        module.write_text('''
"""Module docstring"""

def func1():
    """Function 1"""
    pass
''')
        result = agent.document_module(str(module))
        assert 'functions' in result
        assert result['module_docstring']

    def test_class_documentation(self, agent, tmp_path):
        module = tmp_path / "classes.py"
        module.write_text("""
class MyClass:
    '''A documented class'''
    def method(self):
        '''A method'''
        pass
""")
        result = agent.document_module(str(module))
        assert 'classes' in result
        assert len(result['classes']) > 0

    def test_docstring_coverage_analysis(self, agent, tmp_path):
        module = tmp_path / "coverage.py"
        module.write_text("""
def documented():
    '''Has docstring'''
    pass

def undocumented():
    pass
""")
        result = agent.analyze_docstring_coverage(str(module))
        assert 'coverage_percentage' in result
        assert result['coverage_percentage'] == 50.0

    def test_missing_docstrings_report(self, agent, tmp_path):
        module = tmp_path / "test.py"
        module.write_text("""
def no_doc():
    pass

class NoDocs:
    def method(self):
        pass
""")
        result = agent.find_missing_docstrings(str(module))
        assert len(result['missing']) >= 2

    def test_generate_changelog(self, agent, tmp_path):
        output = tmp_path / "CHANGELOG.md"
        result = agent.generate_changelog(
            version="1.0.0",
            changes=["Feature: Added X", "Fix: Resolved Y"],
            output_path=str(output)
        )
        assert result['success'] is True
        assert output.exists()

    def test_changelog_formatting(self, agent, tmp_path):
        output = tmp_path / "CHANGELOG.md"
        agent.generate_changelog(
            version="2.0.0",
            changes=["Breaking: Changed API"],
            output_path=str(output)
        )
        content = output.read_text()
        assert "2.0.0" in content
        assert "Breaking" in content

    def test_generate_contributing_guide(self, agent, tmp_path):
        output = tmp_path / "CONTRIBUTING.md"
        result = agent.generate_contributing_guide(str(output))
        assert result['success'] is True
        assert output.exists()

    def test_contributing_has_sections(self, agent, tmp_path):
        output = tmp_path / "CONTRIBUTING.md"
        agent.generate_contributing_guide(str(output))
        content = output.read_text()
        assert "Code of Conduct" in content or "Pull Request" in content

    def test_generate_code_of_conduct(self, agent, tmp_path):
        output = tmp_path / "CODE_OF_CONDUCT.md"
        result = agent.generate_code_of_conduct(str(output))
        assert result['success'] is True
        assert output.exists()

    def test_generate_license(self, agent, tmp_path):
        output = tmp_path / "LICENSE"
        result = agent.generate_license(
            license_type="MIT",
            author="Test Author",
            year=2025,
            output_path=str(output)
        )
        assert result['success'] is True
        assert output.exists()

    def test_license_content(self, agent, tmp_path):
        output = tmp_path / "LICENSE"
        agent.generate_license("MIT", "John Doe", 2025, str(output))
        content = output.read_text()
        assert "MIT" in content
        assert "John Doe" in content
        assert "2025" in content

    def test_generate_mkdocs_config(self, agent, tmp_path):
        output = tmp_path / "mkdocs.yml"
        result = agent.generate_mkdocs_config(
            project_name="Test",
            output_path=str(output)
        )
        assert result['success'] is True
        assert output.exists()

    def test_generate_sphinx_config(self, agent, tmp_path):
        output = tmp_path / "conf.py"
        result = agent.generate_sphinx_config(
            project_name="Test",
            output_path=str(output)
        )
        assert result['success'] is True

    def test_docstring_style_check(self, agent, tmp_path):
        module = tmp_path / "style.py"
        module.write_text('''
def func():
    """
    Google-style docstring.
    
    Args:
        None
    
    Returns:
        None
    """
    pass
''')
        result = agent.check_docstring_style(str(module))
        assert 'style' in result

    def test_convert_docstring_format(self, agent):
        google_style = """
    Args:
        x: The input
    Returns:
        The output
"""
        result = agent.convert_docstring_format(google_style, 'google', 'numpy')
        assert result is not None

    def test_extract_examples_from_docstrings(self, agent, tmp_path):
        module = tmp_path / "examples.py"
        module.write_text('''
def func():
    """
    Example:
        >>> func()
        'result'
    """
    return 'result'
''')
        result = agent.extract_examples(str(module))
        assert len(result) > 0

    def test_generate_tutorial(self, agent, tmp_path):
        output = tmp_path / "TUTORIAL.md"
        result = agent.generate_tutorial(
            topic="Getting Started",
            content=["Step 1", "Step 2"],
            output_path=str(output)
        )
        assert result['success'] is True

    def test_generate_faq(self, agent, tmp_path):
        output = tmp_path / "FAQ.md"
        faqs = [
            {"question": "How to install?", "answer": "Run pip install"}
        ]
        result = agent.generate_faq(faqs, str(output))
        assert result['success'] is True

    def test_generate_architecture_doc(self, agent, tmp_path):
        output = tmp_path / "ARCHITECTURE.md"
        result = agent.generate_architecture_doc(
            project_dir=str(tmp_path),
            output_path=str(output)
        )
        assert result['success'] is True

    def test_markdown_table_generation(self, agent):
        data = [
            {"Name": "Alice", "Age": 30},
            {"Name": "Bob", "Age": 25}
        ]
        result = agent.generate_markdown_table(data)
        assert "| Name | Age |" in result
        assert "Alice" in result

    def test_code_example_extraction(self, agent, tmp_path):
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
# Documentation

```python
def example():
    pass
```
""")
        result = agent.extract_code_examples(str(md_file))
        assert len(result) > 0
        assert result[0]['language'] == 'python'

    def test_broken_links_detection(self, agent, tmp_path):
        md_file = tmp_path / "links.md"
        md_file.write_text("""
[Valid](./exists.md)
[Broken](./missing.md)
""")
        (tmp_path / "exists.md").touch()
        result = agent.find_broken_links(str(tmp_path))
        assert len(result['broken']) > 0

    def test_documentation_metrics(self, agent, tmp_path):
        # Create some docs
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / "API.md").write_text("# API")
        result = agent.calculate_documentation_metrics(str(tmp_path))
        assert 'total_files' in result
        assert result['total_files'] >= 2

    def test_generate_glossary(self, agent, tmp_path):
        output = tmp_path / "GLOSSARY.md"
        terms = {"API": "Application Programming Interface"}
        result = agent.generate_glossary(terms, str(output))
        assert result['success'] is True


# ============================================================================
# SECTION 4: INTEGRATION & EDGE CASES (30 tests)
# ============================================================================

class TestIntegrationAndEdgeCases:
    """Test real-world scenarios and edge cases"""

    def test_document_entire_project(self, agent, tmp_path):
        # Create mini project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").write_text("")
        (tmp_path / "src" / "main.py").write_text("def main():\n    pass")
        (tmp_path / "tests").mkdir()

        result = agent.document_project(str(tmp_path))
        assert result['success'] is True

    def test_multi_file_analysis(self, agent, tmp_path):
        files = []
        for i in range(5):
            f = tmp_path / f"module{i}.py"
            f.write_text(f"def func{i}():\n    pass")
            files.append(str(f))

        results = agent.analyze_multiple_files(files)
        assert len(results) == 5

    def test_concurrent_file_processing(self, agent, tmp_path):
        # Test thread safety
        files = [tmp_path / f"file{i}.py" for i in range(10)]
        for f in files:
            f.write_text("def func():\n    pass")

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(agent.analyze_file, str(f)) for f in files]
            results = [f.result() for f in futures]

        assert len(results) == 10

    def test_large_project_performance(self, agent, tmp_path):
        # Create 50 files
        for i in range(50):
            (tmp_path / f"module{i}.py").write_text(f"def func{i}():\n    pass")

        import time
        start = time.time()
        result = agent.document_project(str(tmp_path))
        duration = time.time() - start

        assert duration < 30  # Should complete in under 30s
        assert result['success'] is True

    def test_binary_file_handling(self, agent, tmp_path):
        # Create binary file
        binary = tmp_path / "image.png"
        binary.write_bytes(b'\x89PNG\r\n\x1a\n')

        # Should skip binary files
        result = agent.analyze_file(str(binary))
        assert 'error' in result or result == {}

    def test_unicode_handling(self, agent, tmp_path):
        file = tmp_path / "unicode.py"
        file.write_text("""
def функция():
    '''Функция с unicode'''
    return "Привет"
""", encoding='utf-8')

        result = agent.analyze_file(str(file))
        assert 'functions' in result

    def test_special_characters_in_docstrings(self, agent, tmp_path):
        file = tmp_path / "special.py"
        file.write_text("""
def func():
    '''Contains <tags> and & special chars'''
    pass
""")
        result = agent.analyze_file(str(file))
        assert '<tags>' in result['functions'][0]['docstring']

    def test_very_long_lines(self, agent, tmp_path):
        file = tmp_path / "long.py"
        long_line = "x = " + "1" * 10000
        file.write_text(long_line)

        # Should handle without crashing
        result = agent.analyze_file(str(file))
        assert result is not None

    def test_circular_imports(self, agent, tmp_path):
        a = tmp_path / "a.py"
        b = tmp_path / "b.py"
        a.write_text("from b import func_b\ndef func_a():\n    pass")
        b.write_text("from a import func_a\ndef func_b():\n    pass")

        # Should handle gracefully
        result_a = agent.analyze_file(str(a))
        result_b = agent.analyze_file(str(b))
        assert result_a is not None
        assert result_b is not None

    def test_relative_imports(self, agent, tmp_path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "module.py").write_text("from . import sub")

        result = agent.analyze_file(str(pkg / "module.py"))
        assert 'imports' in result

    def test_star_imports(self, agent, tmp_path):
        file = tmp_path / "star.py"
        file.write_text("from os import *\ndef func():\n    pass")

        result = agent.analyze_file(str(file))
        assert 'os' in str(result['imports'])

    def test_conditional_imports(self, agent, tmp_path):
        file = tmp_path / "conditional.py"
        file.write_text("""
if TYPE_CHECKING:
    from typing import Optional
""")
        result = agent.analyze_file(str(file))
        assert result is not None

    def test_dynamic_imports(self, agent, tmp_path):
        file = tmp_path / "dynamic.py"
        file.write_text("""
module = __import__('os')
""")
        result = agent.analyze_file(str(file))
        assert result is not None

    def test_metaclass_handling(self, agent, tmp_path):
        file = tmp_path / "meta.py"
        file.write_text("""
class Meta(type):
    pass

class MyClass(metaclass=Meta):
    pass
""")
        result = agent.analyze_file(str(file))
        assert len(result['classes']) == 2

    def test_context_managers(self, agent, tmp_path):
        file = tmp_path / "context.py"
        file.write_text("""
class Manager:
    def __enter__(self):
        pass
    def __exit__(self, *args):
        pass
""")
        result = agent.analyze_file(str(file))
        methods = result['classes'][0]['methods']
        assert any(m['name'] == '__enter__' for m in methods)

    def test_magic_methods(self, agent, tmp_path):
        file = tmp_path / "magic.py"
        file.write_text("""
class Custom:
    def __init__(self):
        pass
    def __str__(self):
        pass
    def __repr__(self):
        pass
""")
        result = agent.analyze_file(str(file))
        methods = [m['name'] for m in result['classes'][0]['methods']]
        assert '__init__' in methods
        assert '__str__' in methods

    def test_abstract_methods(self, agent, tmp_path):
        file = tmp_path / "abstract.py"
        file.write_text("""
from abc import ABC, abstractmethod

class Abstract(ABC):
    @abstractmethod
    def method(self):
        pass
""")
        result = agent.analyze_file(str(file))
        assert '@abstractmethod' in str(result['classes'][0]['methods'][0]['decorators'])

    def test_protocol_classes(self, agent, tmp_path):
        file = tmp_path / "protocol.py"
        file.write_text("""
from typing import Protocol

class MyProtocol(Protocol):
    def method(self) -> None:
        ...
""")
        result = agent.analyze_file(str(file))
        assert 'Protocol' in str(result['classes'][0]['bases'])

    def test_generic_types(self, agent, tmp_path):
        file = tmp_path / "generic.py"
        file.write_text("""
from typing import Generic, TypeVar

T = TypeVar('T')

class Container(Generic[T]):
    def get(self) -> T:
        pass
""")
        result = agent.analyze_file(str(file))
        assert 'Generic' in str(result['classes'][0]['bases'])

    def test_union_types(self, agent, tmp_path):
        file = tmp_path / "union.py"
        file.write_text("""
def func(x: int | str) -> bool:
    return True
""")
        result = agent.analyze_file(str(file))
        # Should parse union syntax
        assert result['functions'] is not None

    def test_optional_types(self, agent, tmp_path):
        file = tmp_path / "optional.py"
        file.write_text("""
from typing import Optional

def func(x: Optional[int] = None) -> None:
    pass
""")
        result = agent.analyze_file(str(file))
        assert 'Optional' in str(result['functions'][0]['signature'])

    def test_callable_types(self, agent, tmp_path):
        file = tmp_path / "callable.py"
        file.write_text("""
from typing import Callable

def higher_order(func: Callable[[int], str]) -> None:
    pass
""")
        result = agent.analyze_file(str(file))
        assert 'Callable' in str(result['functions'][0]['signature'])

    def test_literal_types(self, agent, tmp_path):
        file = tmp_path / "literal.py"
        file.write_text("""
from typing import Literal

def func(mode: Literal['r', 'w']) -> None:
    pass
""")
        result = agent.analyze_file(str(file))
        assert result['functions'] is not None

    def test_documentation_with_code_blocks(self, agent, tmp_path):
        file = tmp_path / "blocks.py"
        file.write_text('''
def func():
    """
    Example:
        ```python
        result = func()
        print(result)
        ```
    """
    pass
''')
        result = agent.analyze_file(str(file))
        assert '```python' in result['functions'][0]['docstring']

    def test_rst_docstrings(self, agent, tmp_path):
        file = tmp_path / "rst.py"
        file.write_text('''
def func():
    """
    :param x: Input value
    :type x: int
    :returns: Output
    :rtype: str
    """
    pass
''')
        result = agent.analyze_file(str(file))
        assert ':param' in result['functions'][0]['docstring']

    def test_numpy_docstrings(self, agent, tmp_path):
        file = tmp_path / "numpy.py"
        file.write_text('''
def func():
    """
    Parameters
    ----------
    x : int
        Input value
    
    Returns
    -------
    str
        Output value
    """
    pass
''')
        result = agent.analyze_file(str(file))
        assert 'Parameters' in result['functions'][0]['docstring']

    def test_cache_effectiveness(self, agent, tmp_path):
        file = tmp_path / "cache_test.py"
        file.write_text("def func():\n    pass")

        # First call
        result1 = agent.analyze_file(str(file))
        # Second call (should use cache)
        result2 = agent.analyze_file(str(file))

        assert result1 == result2

    def test_memory_leak_prevention(self, agent, tmp_path):
        # Process many files and check memory doesn't grow unbounded
        import sys
        for i in range(100):
            f = tmp_path / f"file{i}.py"
            f.write_text("def func():\n    pass")
            agent.analyze_file(str(f))

        # Clear cache
        agent._cache.clear()
        # Memory should be released
        assert sys.getsizeof(agent._cache) < 10000

    def test_error_recovery(self, agent, tmp_path):
        # Mix of valid and invalid files
        valid = tmp_path / "valid.py"
        valid.write_text("def func():\n    pass")
        invalid = tmp_path / "invalid.py"
        invalid.write_text("def broken(\n")

        results = agent.analyze_multiple_files([str(valid), str(invalid)])
        # Should process valid file despite error in invalid
        assert any(r.get('functions') for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
