import setuptools

setuptools.setup(
    name="databarn",
    version="1.5.2",
    author="Eduardo Bandeira",
    author_email='eduardowbandeira@gmail.com',
    description="Supercharged dict • Dot notation • Schema definitions • Type validation • Lightweight in-memory ORM",
    url="https://github.com/eduardo-w-bandeira/databarn",
    packages=setuptools.find_packages(),
    install_requires=['beartype>=0.22,<0.3'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
)
