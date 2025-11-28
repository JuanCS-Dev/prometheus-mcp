"""
Real LLM Tests for DocumentationAgent
Tests with ACTUAL Gemini API calls (no mocks)
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from jdev_cli.agents.documentation import DocumentationAgent
from jdev_cli.core.llm import LLMClient
import os


@pytest.fixture
def doc_agent():
    """Create real DocumentationAgent instance with real LLM"""
    # Set API key
    os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

    # Create real LLM client (it auto-detects Gemini from env)
    llm_client = LLMClient()

    # Create MCP client (simple mock for now)
    class SimpleMCP:
        async def call_tool(self, *args, **kwargs):
            return {"result": "ok"}

    return DocumentationAgent(llm_client=llm_client, mcp_client=SimpleMCP())


class TestRealDocGeneration:
    """Test real documentation generation with LLM"""

    def test_generate_function_docs_real(self, doc_agent):
        """Test generating docs for a real Python function"""
        code = '''
def calculate_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
'''
        result = doc_agent.generate_documentation(
            code=code,
            doc_type="function",
            style="google"
        )

        assert result["success"]
        assert "fibonacci" in result["documentation"].lower()
        assert "param" in result["documentation"].lower() or "args" in result["documentation"].lower()

    def test_generate_class_docs_real(self, doc_agent):
        """Test generating docs for a real Python class"""
        code = '''
class BinaryTree:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None
    
    def insert(self, value):
        if value < self.value:
            if self.left is None:
                self.left = BinaryTree(value)
            else:
                self.left.insert(value)
        else:
            if self.right is None:
                self.right = BinaryTree(value)
            else:
                self.right.insert(value)
'''
        result = doc_agent.generate_documentation(
            code=code,
            doc_type="class",
            style="numpy"
        )

        assert result["success"]
        assert "binarytree" in result["documentation"].lower()
        assert "insert" in result["documentation"].lower()

    def test_generate_module_docs_real(self, doc_agent):
        """Test generating module-level documentation"""
        code = '''
"""Utility functions for data processing"""

def clean_data(data):
    return [x.strip() for x in data if x]

def validate_email(email):
    return "@" in email and "." in email
'''
        result = doc_agent.generate_documentation(
            code=code,
            doc_type="module",
            style="sphinx"
        )

        assert result["success"]
        assert len(result["documentation"]) > 50


class TestRealAPIDocGeneration:
    """Test API documentation with real LLM"""

    def test_generate_rest_api_docs(self, doc_agent):
        """Test REST API documentation generation"""
        code = '''
@app.post("/users")
async def create_user(user: UserCreate):
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    return {"id": db_user.id, "username": db_user.username}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404)
    return user
'''
        result = doc_agent.generate_api_docs(
            code=code,
            api_type="rest"
        )

        assert result["success"]
        docs = result["documentation"].lower()
        assert "post" in docs or "create" in docs
        assert "get" in docs or "retrieve" in docs
        assert "user" in docs


class TestRealReadmeGeneration:
    """Test README generation with real LLM"""

    def test_generate_readme_for_project(self, doc_agent):
        """Test generating README for a real project structure"""
        project_info = {
            "name": "ml-pipeline",
            "description": "Machine learning training pipeline with distributed workers",
            "tech_stack": ["Python", "TensorFlow", "Redis", "Celery"],
            "features": [
                "Distributed training",
                "Real-time monitoring",
                "Model versioning",
                "Auto-scaling workers"
            ]
        }

        result = doc_agent.generate_readme(project_info)

        assert result["success"]
        readme = result["documentation"].lower()
        assert "ml-pipeline" in readme or "machine learning" in readme
        assert "install" in readme or "setup" in readme
        assert "usage" in readme or "getting started" in readme


class TestRealDockerfileDocumentation:
    """Test Dockerfile documentation with real LLM"""

    def test_document_dockerfile(self, doc_agent):
        """Test documenting a real Dockerfile"""
        dockerfile = '''
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
'''
        result = doc_agent.generate_documentation(
            code=dockerfile,
            doc_type="dockerfile",
            style="inline"
        )

        assert result["success"]
        assert "python" in result["documentation"].lower()
        assert "port" in result["documentation"].lower() or "8000" in result["documentation"]


class TestRealComplexScenarios:
    """Test complex real-world scenarios"""

    def test_document_async_context_manager(self, doc_agent):
        """Test documenting complex async code"""
        code = '''
class DatabaseConnection:
    async def __aenter__(self):
        self.conn = await asyncpg.connect(DATABASE_URL)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()
    
    async def execute(self, query: str, *args):
        return await self.conn.fetch(query, *args)
'''
        result = doc_agent.generate_documentation(
            code=code,
            doc_type="class",
            style="google"
        )

        assert result["success"]
        docs = result["documentation"].lower()
        assert "async" in docs or "context" in docs
        assert "database" in docs

    def test_document_decorator_pattern(self, doc_agent):
        """Test documenting decorator patterns"""
        code = '''
def retry(max_attempts=3, delay=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
'''
        result = doc_agent.generate_documentation(
            code=code,
            doc_type="function",
            style="numpy"
        )

        assert result["success"]
        docs = result["documentation"].lower()
        assert "retry" in docs or "decorator" in docs
        assert "attempt" in docs or "max_attempts" in docs


class TestRealEdgeCases:
    """Test edge cases with real LLM"""

    def test_empty_code(self, doc_agent):
        """Test handling empty code"""
        result = doc_agent.generate_documentation(
            code="",
            doc_type="function",
            style="google"
        )

        assert not result["success"]
        assert "error" in result

    def test_malformed_code(self, doc_agent):
        """Test handling malformed code"""
        code = '''
def broken_function(
    # Missing closing paren and body
'''
        result = doc_agent.generate_documentation(
            code=code,
            doc_type="function",
            style="google"
        )

        # Should still attempt to generate docs
        assert result["success"] or "error" in result

    def test_multiple_languages_same_file(self, doc_agent):
        """Test handling mixed-language code"""
        code = '''
def process_data(data):
    """Process data using SQL"""
    query = """
        SELECT * FROM users
        WHERE created_at > NOW() - INTERVAL '7 days'
    """
    return execute_sql(query)
'''
        result = doc_agent.generate_documentation(
            code=code,
            doc_type="function",
            style="google"
        )

        assert result["success"]
        assert "sql" in result["documentation"].lower() or "query" in result["documentation"].lower()


class TestRealPerformance:
    """Test performance with real LLM calls"""

    def test_large_codebase_documentation(self, doc_agent):
        """Test documenting large code blocks"""
        # Generate a large class with many methods
        code = '''
class DataProcessor:
    def __init__(self, config):
        self.config = config
    
'''
        for i in range(10):
            code += f'''
    def process_{i}(self, data):
        return data * {i}
    
'''

        result = doc_agent.generate_documentation(
            code=code,
            doc_type="class",
            style="google"
        )

        assert result["success"]
        assert "dataprocessor" in result["documentation"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
