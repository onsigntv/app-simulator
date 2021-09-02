import distutils
import os
import pathlib
import setuptools
import shutil
import sys

# The directory containing this file
HERE = pathlib.Path(__file__).parent

VERSION = "0.9.0"

DESCRIPTION = (
    "Assist the development of apps for OnSign TV platform by running them locally."
)

# The text of the README file
LONG_DESCRIPTION = (HERE / "README.md").read_text()

REQUIREMENTS = (HERE / "requirements.txt").read_text().splitlines()


if len(sys.argv) > 1 and sys.argv[1] == "develop":
    pre_commit_src = HERE / "hooks/pre-commit"
    pre_commit_dst = HERE / ".git/hooks/pre-commit"
    if pre_commit_dst.exists():
        pre_commit_dst.unlink()

    pre_commit_src_rel = os.path.relpath(pre_commit_src, pre_commit_dst.parent)
    os.symlink(pre_commit_src_rel, pre_commit_dst, target_is_directory=True)


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
        "Programming Language :: Python :: 3.7",
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
    python_requires=">=3.7",
    package_data={
        "app_simulator": [
            "templates/base.html",
            "templates/list_files.html",
            "templates/widget_exceptions.html",
            "templates/widget_form.html",
            "static/shim/events.js",
            "static/shim/Intl.min.js",
        ]
    },
    data_files=[(".", ["requirements.txt"])],
    install_requires=REQUIREMENTS,
    extras_require={"dev": ["black==21.7b0"]},
)
