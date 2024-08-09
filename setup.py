import pathlib

import setuptools

# The directory containing this file
HERE = pathlib.Path(__file__).parent

VERSION = "1.3.1"

DESCRIPTION = (
    "Assist the development of apps for OnSign TV platform by running them locally."
)

# The text of the README file
LONG_DESCRIPTION = (HERE / "README.md").read_text()

REQUIREMENTS = (HERE / "requirements.txt").read_text().splitlines()
REQUIREMENTS_DEV = (HERE / "requirements-dev.txt").read_text().splitlines()


setuptools.setup(
    name="onsigntv-app-simulator",
    author="OnSign TV",
    author_email="support@onsign.tv",
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development",
    ],
    url="https://github.com/onsigntv/app-simulator",
    project_urls={
        "Bug Tracker": "https://github.com/onsigntv/app-simulator/issues",
    },
    license="MIT",
    packages=["app_simulator"],
    entry_points={
        "console_scripts": ["onsigntv-app-simulator = app_simulator.__main__:main"]
    },
    keywords="development onsigntv apps",
    python_requires=">=3.8",
    package_data={
        "app_simulator": [
            "templates/base.html",
            "templates/list_files.html",
            "templates/widget_exceptions.html",
            "templates/widget_form.html",
            "static/shim/Intl.min.js",
            "static/shim/signage.js",
            "static/js/widget_form.js",
        ]
    },
    data_files=[(".", ["requirements.txt", "requirements-dev.txt"])],
    install_requires=REQUIREMENTS,
    extras_require={"dev": REQUIREMENTS_DEV},
)
