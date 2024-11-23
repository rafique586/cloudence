from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="gcp-k8s-monitoring",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="GCP Kubernetes Monitoring and Incident Management System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gcp-k8s-monitoring",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "pylint>=2.17.3",
            "black>=23.3.0",
            "mypy>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "gcp-k8s-monitor=src.cli:main",
        ],
    },
)
