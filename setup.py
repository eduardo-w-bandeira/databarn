import setuptools

setuptools.setup(
    name="databarn",
    version="1.0",
    author="Eduardo Bandeira",
    author_email='eduardowbandeira@gmail.com',
    description="A simple in-memory ORM and data carrier",
    url="https://github.com/eduardo-w-bandeira/databarn",
    packages=setuptools.find_packages(),
    install_requires=['typeguard>=4.3,<5',],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
