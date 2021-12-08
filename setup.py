""" setup for creating pypi package """
import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wolf_ism8",
    version="1.7",
    author="marcschmiedchen",
    author_email="marc.schmiedchen@protonmail.com",
    description="Get data from wolf heating system via ISM8",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=["wolf_ism8"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",   
    ],
)
