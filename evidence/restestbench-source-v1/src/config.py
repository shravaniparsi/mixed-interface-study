"""
Central configuration for project paths and constants.
"""

from pathlib import Path
from dataclasses import dataclass

# Project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
REQUIREMENTS_DIR = DATA_DIR / "requirements"
GOLDEN_TESTS_DIR = DATA_DIR / "tests"
SCENARIOS_FILE = DATA_DIR / "scenarios.jsonl"

# Output directory
OUTPUT_DIR = PROJECT_ROOT / "results"

# Services directory
SERVICES_DIR = PROJECT_ROOT / "services"

# Tools directory
TOOLS_DIR = PROJECT_ROOT / "tools"


@dataclass
class ServiceConfig:
    """Configuration for a specific service."""
    name: str
    port: int
    health_endpoint: str
    source_subdir: str = ""  # Subdirectory containing source code to reset for mutations
    
    
# Service-specific configurations
SERVICE_CONFIGS = {
    "fastapi": ServiceConfig(
        name="fastapi",
        port=8000,
        health_endpoint="/docs",
        source_subdir="backend/app"  # Python source for FastAPI
    ),
    "todoapp": ServiceConfig(
        name="todoapp",
        port=5000,
        health_endpoint="/scalar/v1",
        source_subdir="Todo.Api"  # .NET source for TodoApp
    ),
    #"litellm": ServiceConfig(
    #    name="litellm",
    #    port=4000,
    #    health_endpoint="/health/liveliness",
    #    source_subdir="litellm"  # Python source for LiteLLM
    #),
    #"rbac-user-management": ServiceConfig(
    #    name="rbac-user-management",
    #    port=8091,
    #    health_endpoint="/swagger-ui.html",
    #    source_subdir="src"  # Java source for Spring Boot
    #),
    "nestjs-realworld": ServiceConfig(
        name="nestjs-realworld",
        port=3000,
        health_endpoint="/api/tags",
        source_subdir="src"  # TypeScript source for NestJS
    ),
}


def get_service_config(service_name: str) -> ServiceConfig:
    """Get configuration for a service, with defaults for unknown services."""
    if service_name in SERVICE_CONFIGS:
        return SERVICE_CONFIGS[service_name]
    # Default config for unknown services
    return ServiceConfig(
        name=service_name,
        port=8000,
        health_endpoint="/docs"
    )
