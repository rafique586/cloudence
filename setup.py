# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip()
                    and not line.startswith("#")]

setup(
    name="gcp-sre-agent",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="An AI-powered SRE agent for GCP monitoring and incident management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gcp-sre-agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "flake8>=6.0.0",
            "black>=23.3.0",
            "isort>=5.12.0",
        ]
    },
)
