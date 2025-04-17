from setuptools import find_packages, setup

setup(
    name="gemini_handler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-generativeai>=0.3.0",
        "pyyaml>=6.0",
        "fastapi",
        "uvicorn>=0.20.0",
        "pydantic>=2.0.0",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A powerful Python library for interacting with Google's Gemini API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gemini-handler",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    entry_points={
        'console_scripts': [
            'gemini-server=gemini_handler.cli:main',
        ],
    },
)
