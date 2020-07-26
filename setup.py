import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="attorneycrm-pkg-tjdaley",
    version="0.0.1",
    author="Thomas J. Daley, J.D.",
    author_email="tom@powerdaley.com",
    description="Attorney Client Relationship Management App",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tjdaley/payment_redirect",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)