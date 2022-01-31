from pkg_resources import Requirement
from setuptools import setup, find_packages


#######################################################################################################################

MODULE_VERSION = "1.0.0"
PACKAGE_NAME = 'celigo_image_core'


with open("README.md") as readme_file:
    readme = readme_file.read()


requirements = [          
    "jinja2",
    "pathlib",
    "shutil",
    "subprocess",
    "tempfile",
    "skimage.transform",
    "aicsimageio",
    "aicsimageio.writers"
]

setup(name=PACKAGE_NAME,
      version=MODULE_VERSION,
      description='later',
      long_description= readme,
      author='Brian Whitney',
      author_email='brian.whitney@alleninstitute.org',
      license='Allen Institute Software License'
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