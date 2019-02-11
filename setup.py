import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wolf_ism8",
    version="0.33",
    author="wolfwiz",
    author_email="timtimmy671@yahoo.de",
    description="Get data from wolf heating system via ISM8",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wolfwiz/wolf_ism8",
    packages=["wolf_ism8"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",   
    ],
)
