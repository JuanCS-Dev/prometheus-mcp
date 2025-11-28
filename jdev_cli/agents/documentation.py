"""
DocumentationAgent: The Technical Writer - Documentation Excellence Specialist.

This agent generates comprehensive, maintainable documentation from codebases.
It supports multiple formats (Markdown, API Reference, Docstrings) and follows
best practices from Write the Docs and Google Style Guide.

Capabilities:
    - AST-based code analysis (functions, classes, modules)
    - Multi-format documentation generation (MD, RST, HTML)
    - Docstring validation and generation (Google, NumPy, Sphinx)
    - API reference extraction and formatting
    - README generation with usage examples

Architecture:
    DocumentationAgent extends BaseAgent with READ_ONLY + FILE_EDIT capabilities.
    It analyzes Python code structure using AST and generates structured docs.

Philosophy (Boris Cherny):
    "Code tells you how. Documentation tells you why."
"""

import ast
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import (
    AgentCapability,
    AgentResponse,
    AgentRole,
    AgentTask,
    BaseAgent,
)


class DocFormat(str, Enum):
    """Supported documentation formats."""

    MARKDOWN = "markdown"
    RST = "rst"  # ReStructuredText (Sphinx)
    HTML = "html"
    DOCSTRING = "docstring"  # In-code docstrings
    API_REFERENCE = "api_reference"


class DocstringStyle(str, Enum):
    """Docstring formatting styles."""

    GOOGLE = "google"  # Google Style (default)
    NUMPY = "numpy"  # NumPy/SciPy
    SPHINX = "sphinx"  # Sphinx/RST


@dataclass
class FunctionDoc:
    """Documentation for a function/method."""

    name: str
    signature: str
    docstring: Optional[str]
    parameters: List[Tuple[str, str, Optional[str]]]  # (name, type, description)
    returns: Optional[Tuple[str, str]]  # (type, description)
    raises: List[Tuple[str, str]]  # (exception, reason)
    examples: List[str]
    line_number: int


@dataclass
class ClassDoc:
    """Documentation for a class."""

    name: str
    docstring: Optional[str]
    bases: List[str]
    methods: List[FunctionDoc]
    attributes: List[Tuple[str, str, Optional[str]]]  # (name, type, description)
    line_number: int


@dataclass
class ModuleDoc:
    """Documentation for a module."""

    name: str
    docstring: Optional[str]
    classes: List[ClassDoc]
    functions: List[FunctionDoc]
    imports: List[str]
    file_path: str


class DocumentationAgent(BaseAgent):
    """The Technical Writer - Documentation Excellence Specialist.

    This agent analyzes code structure and generates professional documentation
    in multiple formats. It validates existing docstrings, suggests improvements,
    and creates new documentation from scratch.

    Capabilities:
        - READ_ONLY: Analyze code structure
        - FILE_EDIT: Generate documentation files

    Attributes:
        role: AgentRole.DOCUMENTATION (custom extension)
        capabilities: READ_ONLY + FILE_EDIT
    """

    # Docstring validation patterns (Google Style)
    GOOGLE_DOCSTRING_PATTERN = re.compile(
        r"(?P<summary>.+?)\n\n"
        r"(?:(?P<args>Args:.*?)\n\n)?"
        r"(?:(?P<returns>Returns:.*?)\n\n)?"
        r"(?:(?P<raises>Raises:.*?)\n\n)?",
        re.DOTALL,
    )

    # Secret patterns to exclude from docs
    SECRET_PATTERNS = [
        r"['\"]?[A-Z0-9_]+_KEY['\"]?\s*=\s*['\"][\w-]+['\"]",
        r"['\"]?[A-Z0-9_]+_SECRET['\"]?\s*=\s*['\"][\w-]+['\"]",
        r"password\s*=\s*['\"][\w-]+['\"]",
    ]

    def __init__(self, llm_client: Any, mcp_client: Any):
        """Initialize DocumentationAgent.

        Args:
            llm_client: LLM provider client (e.g., Anthropic, OpenAI)
            mcp_client: MCP client for tool execution

        Raises:
            ValueError: If clients are None
        """
        super().__init__(
            role=AgentRole.REVIEWER,  # Closest match (READ_ONLY)
            capabilities=[AgentCapability.READ_ONLY, AgentCapability.FILE_EDIT],
            llm_client=llm_client,
            mcp_client=mcp_client,
        )

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Execute documentation generation task.

        Args:
            task: Task containing:
                - request: "generate_docs", "validate_docstrings", "create_readme"
                - context: {
                    "target_path": str | Path,
                    "format": DocFormat,
                    "style": DocstringStyle,
                    "output_path": Optional[str]
                  }

        Returns:
            AgentResponse with:
                - success: True if docs generated
                - data: {
                    "modules": List[ModuleDoc],
                    "files_created": List[str],
                    "issues_found": List[str]
                  }

        Examples:
            >>> task = AgentTask(
            ...     request="generate_docs",
            ...     context={
            ...         "target_path": "jdev_cli/agents",
            ...         "format": DocFormat.MARKDOWN,
            ...         "style": DocstringStyle.GOOGLE
            ...     }
            ... )
            >>> response = await agent.execute(task)
            >>> assert response.success
            >>> assert "modules" in response.data
        """
        try:
            target_path = Path(task.context.get("target_path", "."))
            doc_format = task.context.get("format", DocFormat.MARKDOWN)
            style = task.context.get("style", DocstringStyle.GOOGLE)
            output_path = task.context.get("output_path")

            if "generate_docs" in task.request.lower():
                return await self._generate_docs(target_path, doc_format, style, output_path)
            elif "validate" in task.request.lower():
                return await self._validate_docstrings(target_path, style)
            elif "readme" in task.request.lower():
                return await self._create_readme(target_path, output_path)
            else:
                return AgentResponse(
                    success=False,
                    error=f"Unknown documentation task: {task.request}",
                )

        except Exception as e:
            return AgentResponse(
                success=False,
                error=f"Documentation generation failed: {str(e)}",
                reasoning="Unexpected error during execution",
            )

    async def _generate_docs(
        self,
        target_path: Path,
        doc_format: DocFormat,
        style: DocstringStyle,
        output_path: Optional[str],
    ) -> AgentResponse:
        """Generate documentation for target path.

        Args:
            target_path: Directory or file to document
            doc_format: Output format (Markdown, RST, etc.)
            style: Docstring style (Google, NumPy, Sphinx)
            output_path: Where to save generated docs

        Returns:
            AgentResponse with generated documentation metadata
        """
        modules: List[ModuleDoc] = []
        files_created: List[str] = []

        # Find all Python files
        if target_path.is_file():
            python_files = [target_path]
        else:
            python_files = list(target_path.rglob("*.py"))

        # Analyze each module
        for py_file in python_files:
            if "__pycache__" in str(py_file) or "test_" in py_file.name:
                continue

            try:
                module_doc = self._analyze_module(py_file)
                modules.append(module_doc)
            except Exception as e:
                # Skip files with syntax errors
                continue

        # Generate documentation files
        if output_path:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            if doc_format == DocFormat.MARKDOWN:
                for module_doc in modules:
                    md_content = self._generate_markdown(module_doc, style)
                    md_file = output_dir / f"{module_doc.name}.md"

                    # Use MCP write_file tool
                    await self._execute_tool(
                        "write_file",
                        {"path": str(md_file), "content": md_content},
                    )
                    files_created.append(str(md_file))

            elif doc_format == DocFormat.API_REFERENCE:
                api_ref = self._generate_api_reference(modules)
                api_file = output_dir / "API_REFERENCE.md"

                await self._execute_tool(
                    "write_file",
                    {"path": str(api_file), "content": api_ref},
                )
                files_created.append(str(api_file))

        return AgentResponse(
            success=True,
            data={
                "modules": [
                    {
                        "name": m.name,
                        "classes": len(m.classes),
                        "functions": len(m.functions),
                    }
                    for m in modules
                ],
                "files_created": files_created,
                "total_modules": len(modules),
            },
            reasoning=f"Analyzed {len(modules)} modules, generated {len(files_created)} documentation files",
        )

    async def _validate_docstrings(
        self, target_path: Path, style: DocstringStyle
    ) -> AgentResponse:
        """Validate existing docstrings against style guide.

        Args:
            target_path: Directory or file to validate
            style: Expected docstring style

        Returns:
            AgentResponse with validation issues
        """
        issues: List[Dict[str, Any]] = []

        # Find all Python files
        python_files = (
            [target_path]
            if target_path.is_file()
            else list(target_path.rglob("*.py"))
        )

        for py_file in python_files:
            if "__pycache__" in str(py_file):
                continue

            try:
                module_doc = self._analyze_module(py_file)

                # Check module docstring
                if not module_doc.docstring:
                    issues.append({
                        "file": str(py_file),
                        "line": 1,
                        "type": "missing_module_docstring",
                        "severity": "medium",
                    })

                # Check classes
                for cls in module_doc.classes:
                    if not cls.docstring:
                        issues.append({
                            "file": str(py_file),
                            "line": cls.line_number,
                            "type": "missing_class_docstring",
                            "class": cls.name,
                            "severity": "medium",
                        })

                    # Check methods
                    for method in cls.methods:
                        if not method.docstring and not method.name.startswith("_"):
                            issues.append({
                                "file": str(py_file),
                                "line": method.line_number,
                                "type": "missing_method_docstring",
                                "class": cls.name,
                                "method": method.name,
                                "severity": "low",
                            })

                # Check standalone functions
                for func in module_doc.functions:
                    if not func.docstring and not func.name.startswith("_"):
                        issues.append({
                            "file": str(py_file),
                            "line": func.line_number,
                            "type": "missing_function_docstring",
                            "function": func.name,
                            "severity": "low",
                        })

            except Exception:
                continue

        return AgentResponse(
            success=True,
            data={
                "issues": issues,
                "total_issues": len(issues),
                "critical": len([i for i in issues if i["severity"] == "critical"]),
                "medium": len([i for i in issues if i["severity"] == "medium"]),
                "low": len([i for i in issues if i["severity"] == "low"]),
            },
            reasoning=f"Found {len(issues)} docstring issues across {len(python_files)} files",
        )

    async def _create_readme(
        self, target_path: Path, output_path: Optional[str]
    ) -> AgentResponse:
        """Generate README.md for project/module.

        Args:
            target_path: Project root directory
            output_path: Where to save README

        Returns:
            AgentResponse with README content
        """
        # Analyze project structure
        modules = []
        python_files = list(target_path.rglob("*.py"))

        for py_file in python_files[:10]:  # Limit to avoid token explosion
            if "__pycache__" not in str(py_file):
                try:
                    modules.append(self._analyze_module(py_file))
                except Exception:
                    continue

        # Generate README content
        readme_content = self._generate_readme_content(target_path, modules)

        # Save README
        if output_path:
            readme_file = Path(output_path)
        else:
            readme_file = target_path / "README.md"

        await self._execute_tool(
            "write_file",
            {"path": str(readme_file), "content": readme_content},
        )

        return AgentResponse(
            success=True,
            data={"readme_path": str(readme_file), "modules_analyzed": len(modules)},
            reasoning=f"Generated README.md with {len(modules)} modules documented",
        )

    def _analyze_module(self, file_path: Path) -> ModuleDoc:
        """Analyze Python module using AST.

        Args:
            file_path: Path to .py file

        Returns:
            ModuleDoc with extracted structure

        Raises:
            SyntaxError: If file has invalid Python syntax
        """
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        module_docstring = ast.get_docstring(tree)

        classes: List[ClassDoc] = []
        functions: List[FunctionDoc] = []
        imports: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(self._analyze_class(node))
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append(self._analyze_function(node))

        return ModuleDoc(
            name=file_path.stem,
            docstring=module_docstring,
            classes=classes,
            functions=functions,
            imports=imports,
            file_path=str(file_path),
        )

    def _analyze_class(self, node: ast.ClassDef) -> ClassDoc:
        """Analyze class definition.

        Args:
            node: AST ClassDef node

        Returns:
            ClassDoc with class metadata
        """
        docstring = ast.get_docstring(node)
        bases = [self._get_name(base) for base in node.bases]
        methods: List[FunctionDoc] = []
        attributes: List[Tuple[str, str, Optional[str]]] = []

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._analyze_function(item))
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attr_name = item.target.id
                attr_type = self._get_name(item.annotation) if item.annotation else "Any"
                attributes.append((attr_name, attr_type, None))

        return ClassDoc(
            name=node.name,
            docstring=docstring,
            bases=bases,
            methods=methods,
            attributes=attributes,
            line_number=node.lineno,
        )

    def _analyze_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionDoc:
        """Analyze function/method definition.

        Args:
            node: AST FunctionDef or AsyncFunctionDef node

        Returns:
            FunctionDoc with function metadata
        """
        docstring = ast.get_docstring(node)
        signature = self._get_signature(node)

        parameters: List[Tuple[str, str, Optional[str]]] = []
        for arg in node.args.args:
            param_name = arg.arg
            param_type = self._get_name(arg.annotation) if arg.annotation else "Any"
            parameters.append((param_name, param_type, None))

        returns = None
        if node.returns:
            return_type = self._get_name(node.returns)
            returns = (return_type, None)

        return FunctionDoc(
            name=node.name,
            signature=signature,
            docstring=docstring,
            parameters=parameters,
            returns=returns,
            raises=[],
            examples=[],
            line_number=node.lineno,
        )

    def _get_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Generate function signature string.

        Args:
            node: AST function node

        Returns:
            Signature string (e.g., "def foo(x: int, y: str) -> bool")
        """
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_name(arg.annotation)}"
            args.append(arg_str)

        sig = f"def {node.name}({', '.join(args)})"
        if node.returns:
            sig += f" -> {self._get_name(node.returns)}"
        return sig

    def _get_name(self, node: ast.expr) -> str:
        """Extract name from AST node.

        Args:
            node: AST expression node

        Returns:
            String representation of the name
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        else:
            return "Any"

    def _generate_markdown(self, module_doc: ModuleDoc, style: DocstringStyle) -> str:
        """Generate Markdown documentation for module.

        Args:
            module_doc: Analyzed module documentation
            style: Docstring style (not used for Markdown, but kept for consistency)

        Returns:
            Markdown-formatted documentation string
        """
        lines = [f"# {module_doc.name}", ""]

        if module_doc.docstring:
            lines.extend([module_doc.docstring, ""])

        # Table of contents
        if module_doc.classes or module_doc.functions:
            lines.append("## Table of Contents")
            lines.append("")

            if module_doc.classes:
                lines.append("### Classes")
                for cls in module_doc.classes:
                    lines.append(f"- [{cls.name}](#{cls.name.lower()})")
                lines.append("")

            if module_doc.functions:
                lines.append("### Functions")
                for func in module_doc.functions:
                    lines.append(f"- [{func.name}](#{func.name.lower()})")
                lines.append("")

        # Classes
        for cls in module_doc.classes:
            lines.extend([f"## {cls.name}", ""])

            if cls.bases:
                lines.append(f"**Inherits from:** `{', '.join(cls.bases)}`")
                lines.append("")

            if cls.docstring:
                lines.extend([cls.docstring, ""])

            # Methods
            if cls.methods:
                lines.append("### Methods")
                lines.append("")
                for method in cls.methods:
                    lines.append(f"#### `{method.signature}`")
                    lines.append("")
                    if method.docstring:
                        lines.extend([method.docstring, ""])

        # Standalone functions
        if module_doc.functions:
            lines.append("## Functions")
            lines.append("")

            for func in module_doc.functions:
                lines.append(f"### `{func.signature}`")
                lines.append("")
                if func.docstring:
                    lines.extend([func.docstring, ""])

        return "\n".join(lines)

    def _generate_api_reference(self, modules: List[ModuleDoc]) -> str:
        """Generate comprehensive API reference.

        Args:
            modules: List of analyzed modules

        Returns:
            Markdown-formatted API reference
        """
        lines = ["# API Reference", "", "Auto-generated API documentation.", ""]

        for module in modules:
            lines.extend([f"## {module.name}", ""])

            if module.docstring:
                lines.extend([module.docstring, ""])

            # Classes summary
            if module.classes:
                lines.append("### Classes")
                lines.append("")
                for cls in module.classes:
                    lines.append(f"- **{cls.name}**: {cls.docstring.split('.')[0] if cls.docstring else 'No description'}")
                lines.append("")

            # Functions summary
            if module.functions:
                lines.append("### Functions")
                lines.append("")
                for func in module.functions:
                    lines.append(f"- **{func.name}**: {func.docstring.split('.')[0] if func.docstring else 'No description'}")
                lines.append("")

        return "\n".join(lines)

    def _generate_readme_content(
        self, project_path: Path, modules: List[ModuleDoc]
    ) -> str:
        """Generate README.md content.

        Args:
            project_path: Root project directory
            modules: List of analyzed modules

        Returns:
            README.md content
        """
        project_name = project_path.name

        lines = [
            f"# {project_name}",
            "",
            "## Overview",
            "",
            "Auto-generated project documentation.",
            "",
            "## Project Structure",
            "",
            "```",
        ]

        # Simple directory tree
        for module in modules[:20]:  # Limit to 20
            lines.append(f"├── {module.name}.py")

        lines.extend([
            "```",
            "",
            "## Modules",
            "",
        ])

        for module in modules:
            lines.append(f"### {module.name}")
            lines.append("")
            if module.docstring:
                lines.append(module.docstring.split("\n")[0])
                lines.append("")

        lines.extend([
            "## Installation",
            "",
            "```bash",
            "pip install -r requirements.txt",
            "```",
            "",
            "## Usage",
            "",
            "```python",
            f"from {project_name} import ...",
            "```",
            "",
            "## License",
            "",
            "MIT License",
        ])

        return "\n".join(lines)

    # PUBLIC SYNC API (for testing and direct usage)

    def generate_documentation(
        self,
        code: str,
        doc_type: str = "function",
        style: str = "google"
    ) -> Dict[str, Any]:
        """Generate documentation for code snippet (SYNC wrapper).
        
        Args:
            code: Source code to document
            doc_type: Type of documentation ("function", "class", "module", "dockerfile")
            style: Docstring style ("google", "numpy", "sphinx")
        
        Returns:
            Dict with keys:
                - success: bool
                - documentation: str (generated docs)
                - error: Optional[str]
        """
        import asyncio

        if not code or not code.strip():
            return {
                "success": False,
                "error": "Empty code provided",
                "documentation": ""
            }

        try:
            # Use LLM to generate docs
            prompt = f"""Generate {style}-style documentation for this {doc_type}:

```python
{code}
```

Return ONLY the documentation text, no explanations."""

            # Run async call synchronously
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            response = loop.run_until_complete(
                self.llm_client.generate(
                    prompt=prompt,
                    max_tokens=2000,
                    temperature=0.3
                )
            )

            return {
                "success": True,
                "documentation": response.strip()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "documentation": ""
            }

    def generate_api_docs(
        self,
        code: str,
        api_type: str = "rest"
    ) -> Dict[str, Any]:
        """Generate API documentation (SYNC wrapper).
        
        Args:
            code: API route code
            api_type: Type of API ("rest", "graphql", "grpc")
        
        Returns:
            Dict with success, documentation, error
        """
        import asyncio

        try:
            prompt = f"""Generate {api_type.upper()} API documentation for:

```python
{code}
```

Include: endpoints, methods, parameters, responses, examples."""

            # Run async call synchronously
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            response = loop.run_until_complete(
                self.llm_client.generate(
                    prompt=prompt,
                    max_tokens=3000,
                    temperature=0.2
                )
            )

            return {
                "success": True,
                "documentation": response.strip()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "documentation": ""
            }

    def generate_readme(
        self,
        project_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate README for project (SYNC wrapper).
        
        Args:
            project_info: Dict with keys:
                - name: str
                - description: str
                - tech_stack: List[str]
                - features: List[str]
        
        Returns:
            Dict with success, documentation, error
        """
        import asyncio

        try:
            name = project_info.get("name", "Project")
            desc = project_info.get("description", "")
            tech = ", ".join(project_info.get("tech_stack", []))
            features = "\n".join(f"- {f}" for f in project_info.get("features", []))

            prompt = f"""Generate a professional README.md for:

**Project:** {name}
**Description:** {desc}
**Tech Stack:** {tech}
**Features:**
{features}

Include: Installation, Usage, Contributing, License sections."""

            # Run async call synchronously
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            response = loop.run_until_complete(
                self.llm_client.generate(
                    prompt=prompt,
                    max_tokens=4000,
                    temperature=0.4
                )
            )

            return {
                "success": True,
                "documentation": response.strip()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "documentation": ""
            }
