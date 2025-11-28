"""
Tool Factory - Automatic Tool Generation.

References:
- AutoTools (arXiv:2405.16533): LLMs automate tool creation
- ToolFactory: Generate Python functions from documentation

The Tool Factory enables the agent to:
1. Identify when it needs a tool that doesn't exist
2. Generate tool code automatically
3. Test and validate tools in sandbox
4. Register tools for future use
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any, Tuple
import ast
import json
import re
from datetime import datetime


@dataclass
class ToolSpec:
    """Specification of a generated tool."""
    name: str
    description: str
    parameters: Dict[str, dict]  # param_name -> {type, description, required}
    return_type: str
    code: str
    examples: List[dict] = field(default_factory=list)
    success_rate: float = 0.0
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    version: int = 1

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "version": self.version,
        }

    def get_signature(self) -> str:
        """Get function signature string."""
        params = []
        for name, info in self.parameters.items():
            param_type = info.get("type", "Any")
            if info.get("required", True):
                params.append(f"{name}: {param_type}")
            else:
                default = info.get("default", "None")
                params.append(f"{name}: {param_type} = {default}")
        return f"def {self.name}({', '.join(params)}) -> {self.return_type}"


@dataclass
class ToolGenerationRequest:
    """Request to generate a new tool."""
    description: str
    input_examples: List[dict]
    expected_outputs: List[Any]
    constraints: List[str] = field(default_factory=list)
    preferred_name: Optional[str] = None
    max_lines: int = 50


class ToolGenerationError(Exception):
    """Error during tool generation."""
    pass


class ToolFactory:
    """
    Automatic Tool Factory.

    Generates, tests, and registers tools on demand.
    """

    def __init__(self, llm_client, sandbox_executor):
        self.llm = llm_client
        self.sandbox = sandbox_executor
        self.generated_tools: Dict[str, ToolSpec] = {}
        self.builtin_tools: Dict[str, Callable] = {}
        self.generation_history: List[dict] = []

    async def generate_tool(
        self,
        request: ToolGenerationRequest,
        max_attempts: int = 3,
    ) -> ToolSpec:
        """
        Generate a new tool based on description.

        Process:
        1. Use LLM to generate code
        2. Validate syntax
        3. Test in sandbox
        4. Register if successful
        """
        # Generate initial code
        code = await self._generate_code(request)

        # Validate syntax
        if not self._validate_syntax(code):
            code = await self._fix_syntax_errors(code, request)

        # Extract function metadata
        func_name, params, return_type, docstring = self._parse_function(code)

        # Use preferred name if provided
        if request.preferred_name and request.preferred_name != func_name:
            code = code.replace(f"def {func_name}", f"def {request.preferred_name}")
            func_name = request.preferred_name

        # Create spec
        spec = ToolSpec(
            name=func_name,
            description=docstring or request.description,
            parameters=params,
            return_type=return_type,
            code=code,
            examples=request.input_examples,
        )

        # Test the tool
        test_results = await self._test_tool(
            spec,
            request.input_examples,
            request.expected_outputs
        )

        if test_results["success_rate"] >= 0.8:
            spec.success_rate = test_results["success_rate"]
            self.generated_tools[func_name] = spec
            self._log_generation(spec, test_results, success=True)
            return spec

        # Try to improve if initial test failed
        for attempt in range(max_attempts - 1):
            improved_code = await self._improve_tool(
                spec,
                test_results["failures"],
                request
            )

            if improved_code:
                spec.code = improved_code
                spec.version += 1

                test_results = await self._test_tool(
                    spec,
                    request.input_examples,
                    request.expected_outputs
                )

                if test_results["success_rate"] >= 0.8:
                    spec.success_rate = test_results["success_rate"]
                    self.generated_tools[func_name] = spec
                    self._log_generation(spec, test_results, success=True)
                    return spec

        self._log_generation(spec, test_results, success=False)
        raise ToolGenerationError(
            f"Failed to generate working tool after {max_attempts} attempts. "
            f"Last failures: {test_results.get('failures', [])}"
        )

    async def generate_tool_from_example(
        self,
        name: str,
        input_output_pairs: List[Tuple[Any, Any]],
        description: Optional[str] = None,
    ) -> ToolSpec:
        """
        Generate tool from input/output examples only.

        Infers the function logic from examples.
        """
        # Build description from examples
        if not description:
            examples_str = "\n".join([
                f"  {inp} -> {out}"
                for inp, out in input_output_pairs[:5]
            ])
            description = f"Function that transforms inputs as follows:\n{examples_str}"

        request = ToolGenerationRequest(
            description=description,
            input_examples=[{"input": inp} for inp, _ in input_output_pairs],
            expected_outputs=[out for _, out in input_output_pairs],
            preferred_name=name,
        )

        return await self.generate_tool(request)

    async def _generate_code(self, request: ToolGenerationRequest) -> str:
        """Generate initial code using LLM."""
        examples_formatted = self._format_examples(
            request.input_examples,
            request.expected_outputs
        )

        prompt = f"""Generate a Python function that does the following:

DESCRIPTION: {request.description}

INPUT/OUTPUT EXAMPLES:
{examples_formatted}

CONSTRAINTS:
{chr(10).join(f'- {c}' for c in request.constraints) if request.constraints else '- None specified'}

Requirements:
1. Function must be self-contained (no external dependencies beyond stdlib)
2. Must have type hints for all parameters and return value
3. Must have a docstring explaining what it does
4. Must handle edge cases gracefully
5. Must be efficient and not exceed {request.max_lines} lines
6. Function name should be descriptive (use {request.preferred_name or 'a descriptive name'})

Output ONLY the function code, no explanations:
```python
def function_name(...):
    \"\"\"Docstring.\"\"\"
    ...
```"""

        response = await self.llm.generate(prompt)
        return self._extract_code(response)

    async def _test_tool(
        self,
        spec: ToolSpec,
        inputs: List[dict],
        expected: List[Any],
    ) -> dict:
        """Test tool in sandbox against examples."""
        successes = 0
        failures = []

        for i, (inp, exp) in enumerate(zip(inputs, expected)):
            # Build test code
            if isinstance(inp, dict) and "input" in inp:
                # Single input wrapped in dict
                call_code = f"result = {spec.name}({repr(inp['input'])})"
            elif isinstance(inp, dict):
                # Multiple kwargs
                kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in inp.items())
                call_code = f"result = {spec.name}({kwargs_str})"
            else:
                # Single positional arg
                call_code = f"result = {spec.name}({repr(inp)})"

            test_code = f"""
{spec.code}

# Test execution
try:
    {call_code}

    expected = {repr(exp)}
    passed = result == expected

    import json
    print(json.dumps({{"passed": passed, "result": repr(result), "expected": repr(expected)}}))
except Exception as e:
    import json
    print(json.dumps({{"passed": False, "error": str(e)}}))
"""

            try:
                result = await self.sandbox.execute(test_code, timeout=10)

                if result.success:
                    # Parse output
                    try:
                        output = json.loads(result.stdout.strip().split('\n')[-1])
                        if output.get("passed"):
                            successes += 1
                        else:
                            failures.append({
                                "test_case": i + 1,
                                "input": inp,
                                "expected": exp,
                                "got": output.get("result"),
                                "error": output.get("error"),
                            })
                    except json.JSONDecodeError:
                        failures.append({
                            "test_case": i + 1,
                            "input": inp,
                            "expected": exp,
                            "error": f"Invalid output: {result.stdout}",
                        })
                else:
                    failures.append({
                        "test_case": i + 1,
                        "input": inp,
                        "expected": exp,
                        "error": result.stderr or result.error_message,
                    })

            except Exception as e:
                failures.append({
                    "test_case": i + 1,
                    "input": inp,
                    "expected": exp,
                    "error": str(e),
                })

        total = len(inputs)
        return {
            "success_rate": successes / max(total, 1),
            "passed": successes,
            "failed": len(failures),
            "total": total,
            "failures": failures,
        }

    async def _improve_tool(
        self,
        spec: ToolSpec,
        failures: List[dict],
        request: ToolGenerationRequest,
    ) -> Optional[str]:
        """Improve a tool based on test failures."""
        failures_formatted = "\n".join([
            f"Test {f['test_case']}: Input={f.get('input')}, Expected={f.get('expected')}, "
            f"Got={f.get('got', 'N/A')}, Error={f.get('error', 'None')}"
            for f in failures[:5]  # Limit to 5 failures
        ])

        prompt = f"""The following Python function has bugs. Fix them.

ORIGINAL CODE:
```python
{spec.code}
```

TEST FAILURES:
{failures_formatted}

ORIGINAL REQUIREMENTS:
{request.description}

Fix the bugs and output the corrected code only:
```python
def {spec.name}(...):
    ...
```"""

        response = await self.llm.generate(prompt)
        improved_code = self._extract_code(response)

        if self._validate_syntax(improved_code):
            return improved_code

        return None

    async def _fix_syntax_errors(
        self,
        code: str,
        request: ToolGenerationRequest,
    ) -> str:
        """Fix syntax errors in generated code."""
        try:
            ast.parse(code)
            return code  # No syntax errors
        except SyntaxError as e:
            error_msg = str(e)

        prompt = f"""Fix the syntax error in this Python code:

```python
{code}
```

ERROR: {error_msg}

Output only the corrected code:
```python
...
```"""

        response = await self.llm.generate(prompt)
        fixed_code = self._extract_code(response)

        if self._validate_syntax(fixed_code):
            return fixed_code

        return code  # Return original if fix failed

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool function by name."""
        # Check builtin first
        if name in self.builtin_tools:
            return self.builtin_tools[name]

        # Check generated
        if name in self.generated_tools:
            spec = self.generated_tools[name]
            spec.usage_count += 1
            spec.last_used = datetime.now()

            # Compile and return function
            exec_globals = {}
            exec(spec.code, exec_globals)
            return exec_globals.get(name)

        return None

    def get_tool_spec(self, name: str) -> Optional[ToolSpec]:
        """Get tool specification."""
        return self.generated_tools.get(name)

    def list_tools(self) -> List[dict]:
        """List all available tools."""
        tools = []

        # Builtin tools
        for name, func in self.builtin_tools.items():
            tools.append({
                "name": name,
                "type": "builtin",
                "description": func.__doc__ or "No description",
            })

        # Generated tools
        for name, spec in self.generated_tools.items():
            tools.append({
                "name": name,
                "type": "generated",
                "description": spec.description,
                "success_rate": spec.success_rate,
                "usage_count": spec.usage_count,
                "parameters": list(spec.parameters.keys()),
            })

        return tools

    def register_builtin(self, name: str, func: Callable):
        """Register a builtin tool."""
        self.builtin_tools[name] = func

    def register_generated(self, spec: ToolSpec):
        """Register a pre-generated tool spec."""
        self.generated_tools[spec.name] = spec

    def remove_tool(self, name: str) -> bool:
        """Remove a generated tool."""
        if name in self.generated_tools:
            del self.generated_tools[name]
            return True
        return False

    def _extract_code(self, text: str) -> str:
        """Extract Python code from LLM response."""
        # Try to find code block
        code_match = re.search(r'```python\n(.*?)```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Try generic code block
        code_match = re.search(r'```\n(.*?)```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Return as-is if no code block found
        return text.strip()

    def _validate_syntax(self, code: str) -> bool:
        """Validate Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _parse_function(self, code: str) -> Tuple[str, dict, str, Optional[str]]:
        """Extract function metadata from code."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return "unknown", {}, "Any", None

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                name = node.name

                # Parse parameters
                params = {}
                for arg in node.args.args:
                    param_name = arg.arg
                    param_type = "Any"
                    if arg.annotation:
                        try:
                            param_type = ast.unparse(arg.annotation)
                        except:
                            param_type = "Any"
                    params[param_name] = {
                        "type": param_type,
                        "required": True,
                    }

                # Handle defaults
                defaults = node.args.defaults
                num_defaults = len(defaults)
                param_names = list(params.keys())
                for i, default in enumerate(defaults):
                    param_idx = len(param_names) - num_defaults + i
                    if param_idx < len(param_names):
                        params[param_names[param_idx]]["required"] = False
                        try:
                            params[param_names[param_idx]]["default"] = ast.unparse(default)
                        except:
                            pass

                # Parse return type
                return_type = "Any"
                if node.returns:
                    try:
                        return_type = ast.unparse(node.returns)
                    except:
                        return_type = "Any"

                # Parse docstring
                docstring = ast.get_docstring(node)

                return name, params, return_type, docstring

        return "unknown", {}, "Any", None

    def _format_examples(
        self,
        inputs: List[dict],
        outputs: List[Any],
    ) -> str:
        """Format input/output examples for prompt."""
        lines = []
        for i, (inp, out) in enumerate(zip(inputs, outputs), 1):
            if isinstance(inp, dict) and "input" in inp:
                inp_str = repr(inp["input"])
            else:
                inp_str = repr(inp)
            lines.append(f"  Example {i}: {inp_str} -> {repr(out)}")
        return "\n".join(lines)

    def _log_generation(
        self,
        spec: ToolSpec,
        test_results: dict,
        success: bool,
    ):
        """Log tool generation attempt."""
        self.generation_history.append({
            "tool_name": spec.name,
            "success": success,
            "test_results": test_results,
            "timestamp": datetime.now().isoformat(),
            "version": spec.version,
        })

    def export_tools(self) -> dict:
        """Export all generated tools."""
        return {
            name: {
                **spec.to_dict(),
                "code": spec.code,
            }
            for name, spec in self.generated_tools.items()
        }

    def import_tools(self, data: dict):
        """Import previously exported tools."""
        for name, tool_data in data.items():
            spec = ToolSpec(
                name=tool_data["name"],
                description=tool_data["description"],
                parameters=tool_data["parameters"],
                return_type=tool_data["return_type"],
                code=tool_data["code"],
                success_rate=tool_data.get("success_rate", 0),
                usage_count=tool_data.get("usage_count", 0),
                version=tool_data.get("version", 1),
            )
            self.generated_tools[name] = spec

    def get_stats(self) -> dict:
        """Get tool factory statistics."""
        return {
            "builtin_tools": len(self.builtin_tools),
            "generated_tools": len(self.generated_tools),
            "total_generations": len(self.generation_history),
            "successful_generations": sum(
                1 for h in self.generation_history if h["success"]
            ),
            "total_tool_uses": sum(
                spec.usage_count for spec in self.generated_tools.values()
            ),
        }
