from setuptools import find_packages, setup


name = 'emptor-web-scraper'
version = "0.0.1"

with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name=name,
    version=version,
    author="Faith Kangai",
    author_email="faithkangai.g@gmail.com",
    license="MIT",
    description="Project to process documents from the web",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fey101/emptor_web_scraper",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
    ],
    install_requires=[
        "requests",
        "beautifulsoup4",
    ]
)
