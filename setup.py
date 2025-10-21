import setuptools
import sys
import platform

# Check if running on macOS
if platform.system() != "Darwin":
    sys.stderr.write("Error: sisypho-sdk is only supported on macOS\n")
    sys.exit(1)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sisypho",
    version="0.1.0",
    author="Harishguna S",
    author_email="your.email@example.com",  # Update this with your actual email
    description="An SDK for browser automation, workflow recording, and skill execution with MCP integration (macOS only)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HarishgunaS/sisypho-sdk",
    packages=setuptools.find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    package_data={
        "sisypho.integrations.macos": ["servers/**/*"],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.8",
    install_requires=[
        "playwright>=1.40.0",
        "openpyxl>=3.1.0",
        "pycryptodomex>=3.23.0",
        "pyotp>=2.0.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
        "full": [
            "pillow>=10.0.0",
            "numpy>=1.24.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
        ],
    },
    keywords="automation, browser, workflow, recording, MCP, skills, playwright",
    project_urls={
        "Bug Reports": "https://github.com/HarishgunaS/sisypho-sdk/issues",
        "Source": "https://github.com/HarishgunaS/sisypho-sdk",
    },
)