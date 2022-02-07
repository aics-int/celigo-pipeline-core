from pkg_resources import Requirement
from setuptools import setup, find_packages


#######################################################################################################################

MODULE_VERSION = "1.0.0"
PACKAGE_NAME = 'celigo_image_core'


with open("README.md") as readme_file:
    readme = readme_file.read()


requirements = [          
    #"jinja2>=3.0.0",
    #"skimage.transform>= 0.19.0",
    #"aicsimageio>=4.0.0",
    #"aicsimageio.writers>=4.0.0"
]

setup(name=PACKAGE_NAME,
    version=MODULE_VERSION,
    description='later',
    long_description= readme,
    author='Brian Whitney',
    author_email='brian.whitney@alleninstitute.org',
    license='Allen Institute Software License',
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: Free for non-commercial use",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ]
      )


"""
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import shutil
import subprocess
import tempfile

from skimage.transform import rescale
from aicsimageio import AICSImage
from aicsimageio.writers import OmeTiffWriter

class CeligoSingleImageCore:
"""