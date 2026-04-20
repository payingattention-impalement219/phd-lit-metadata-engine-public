from setuptools import find_packages, setup


setup(
    name="phd-lit-metadata-backend",
    version="0.1.0",
    description="Local scholarly metadata harvesting backend for PhD literature searches",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.110",
        "uvicorn[standard]>=0.27",
        "httpx>=0.27",
        "pydantic>=2.6",
        "python-dotenv>=1.0",
        "PyYAML>=6.0",
        "pandas>=2.1",
        "openpyxl>=3.1",
        "rapidfuzz>=3.6",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0",
            "pytest-asyncio>=0.23",
            "ruff>=0.4",
            "jupyterlab>=4.0",
            "matplotlib>=3.8",
        ]
    },
)

