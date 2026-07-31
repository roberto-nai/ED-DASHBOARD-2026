from setuptools import setup, find_packages

setup(
    name="ed_dashboard",
    version="0.1.0",
    description="Emergency Department Dashboard",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",
        "streamlit>=1.28.0",
        "pm4py>=2.7.0",
        "pyyaml>=6.0",
        "watchdog>=3.0.0",
        "matplotlib>=3.7.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.10",
    ],
)
