"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              AGENTE JUSTIÇA                                  ║
║                    Sistema de Governança Multi-Agente                        ║
║                           Setup de Instalação                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from setuptools import setup, find_packages
from pathlib import Path

# Ler README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="justica",
    version="3.0.0",
    author="Claude (Anthropic) + Humanidade",
    author_email="governance@future.ai",
    description="Sistema de Governança Multi-Agente - Agente JUSTIÇA",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/future-governance/justica",
    project_urls={
        "Documentation": "https://justica.readthedocs.io",
        "Bug Tracker": "https://github.com/future-governance/justica/issues",
        "Source Code": "https://github.com/future-governance/justica",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Security",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    python_requires=">=3.10",
    install_requires=[
        # Core - sem dependências externas obrigatórias para máxima portabilidade
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "pytest-cov>=4.0",
            "mypy>=1.0",
            "black>=23.0",
            "ruff>=0.1",
            "pre-commit>=3.0",
        ],
        "langgraph": [
            "langgraph>=0.1",
            "langchain>=0.1",
        ],
        "observability": [
            "prometheus-client>=0.17",
            "opentelemetry-api>=1.20",
            "opentelemetry-sdk>=1.20",
        ],
        "all": [
            "langgraph>=0.1",
            "langchain>=0.1",
            "prometheus-client>=0.17",
            "opentelemetry-api>=1.20",
            "opentelemetry-sdk>=1.20",
        ],
    },
    entry_points={
        "console_scripts": [
            "justica=justica.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "ai",
        "governance",
        "multi-agent",
        "security",
        "constitutional-ai",
        "llm",
        "trust",
        "enforcement",
        "monitoring",
        "audit",
    ],
)
