from setuptools import find_packages, setup

setup(
    name="gemini_handler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-generativeai>=0.3.0",
        "pyyaml>=6.0",
    ],
)
