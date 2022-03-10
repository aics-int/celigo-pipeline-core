from jinja2 import Environment, PackageLoader
from pathlib import Path
import shutil
import subprocess
import tempfile
import os
import numpy as np
import importlib.resources as pkg_resources

from skimage.transform import rescale
from aicsimageio import AICSImage
from aicsimageio.writers import OmeTiffWriter
from . import pipelines

class CeligoSingleImageCore:

    """
    This Class provides utility functions for the Celigo pipeline to prepare single images for:

    1) Ilastik Processing

    2) Cell Profiler Processing

    Given its large processing needs it is set up to run on slurm

    """

    def __init__(self, raw_image_path):

        # Specific name of experiment
        self.tempdirname = Path(raw_image_path).with_suffix('').name

        # Working Directory
        if not os.path.exists(f'/home/brian.whitney/{self.tempdirname}'): # NEEDS TO CHANGE TO HOME/USER
            os.mkdir(f'/home/brian.whitney/{self.tempdirname}') # NEEDS TO CHANGE TO HOME/USER
        # self.temp_dir = tempfile.TemporaryDirectory(dir='~/')
        self.working_dir= Path(f'/home/brian.whitney/{self.tempdirname}') # NEEDS TO CHANGE TO HOME/USER

        # Image Paths
        self.raw_image_path = Path(raw_image_path)
        shutil.copyfile(self.raw_image_path, f'{self.working_dir}/{self.raw_image_path.name}')
        self.image_path =  Path(f'{self.working_dir}/{self.raw_image_path.name}')

        # Future resource paths 
        self.filelist_path = Path()
        self.resize_filelist_path = Path()
        self.cell_profiler_output_path = Path()

        # Pipeline paths for templates
        with pkg_resources.path(pipelines, "rescale_pipeline.cppipe") as p:
            self.rescale_pipeline_path= p
        with pkg_resources.path(pipelines, "rescale_pipeline.cppipe") as p:
            self.cellprofiler_pipeline_path= p

        # self.rescale_pipeline_path = importlib.resources.path('celigo_image_core.pipelines','rescale_pipeline.cppipe')
        # self.ilastik_pipeline_path = importlib.resources.path('celigo_image_core.pipelines', 'ballingandlifting.ilp') This file is currently huge and should not be imported with package
        # self.cellprofiler_pipeline_path = importlib.resources.path('celigo_image_core.pipelines', '96_well_colony_pipeline.cppipe')

    def downsample(self):
        """ 
        FUNCTIONALITY: This method takes an existing image and creates a copy of the image scaled by a given 
        quantity/magnification. Ex. 4 --> 1/4 size.
        """
        # Generates a filelist
        with open(self.working_dir / 'resize_filelist.txt', 'w+') as rfl:
            rfl.write(str(self.image_path) + '\n')

        self.resize_filelist_path = self.working_dir / 'resize_filelist.txt'

        # Defines variables for bash script
        script_config = {

            'filelist_path': str(self.resize_filelist_path),
            'output_path': str(self.working_dir),
            'pipeline_path': str(self.rescale_pipeline_path)
        }

        # Generates script_body from existing templates.
        jinja_env = Environment(loader=PackageLoader(package_name = 'celigo_image_core', package_path= 'templates'))
        script_body = jinja_env.get_template('resize_cellprofiler_template.j2').render(script_config)

        # Creates bash script locally.
        with open(self.working_dir / 'resize.sh', 'w+') as rsh:
            rsh.write(script_body)

        # Runs resize on slurm
        subprocess.run(['sbatch', f'{str(self.working_dir)}/resize.sh'], check = True)

        # Sets path to resized image to image path for future use  
        self.image_path = self.image_path.parent / f"{self.image_path.with_suffix('').name}_rescale.tiff"

    def run_ilastik(self):

        """
        FUNCTIONALITY: This method takes an existing image either scaled or unscaled and creates a probability 
        map of [I DON'T KNOW]. It does this by creating a bash script, given above parameters, running said script 
        on the slurm cluster in a pre-existing virtual environment and then generating a list of pertinent files
        called filelist.txt (containing the path to the image and to the probability map). This file is necessary
        to run CellProfiler.
        """
        # Parameters to input to bash script template 
        script_config = {
            'image_path': f"'{str( self.image_path)}'",
            'output_path': f"'{str(self.image_path.with_suffix(''))}_probabilities.tiff'"
        }

        # Generates script_body from existing templates.
        jinja_env = Environment(loader=PackageLoader(package_name = 'celigo_image_core', package_path= 'templates'))
        # jinja_env = Environment(loader=FileSystemLoader('/allen/aics/microscopy/brian_whitney/templates'))
        script_body = jinja_env.get_template('ilastik_template.j2').render(script_config)

        # Creates bash script locally.
        with open(self.working_dir / 'ilastik.sh', 'w+') as rsh:
            rsh.write(script_body)

        # Runs ilastik on slurm
        subprocess.run(['sbatch', f'{str(self.working_dir)}/ilastik.sh'], check = True)

        # Creates filelist.txt
        with open(self.working_dir / 'filelist.txt', 'w+') as rfl:
            rfl.write(str(self.image_path) + '\n')
            # Have to use .with_suffix twice becasue of the .ome.tiff file suffix
            rfl.write( str(self.image_path.with_suffix('')) + '_probabilities.tiff')

        self.filelist_path = self.working_dir / 'filelist.txt'

    def run_cellprofiler(self) -> Path:

        """
        FUNCTIONALITY: This method takes aa path to a filelist.txt file and creates a directory with a myriad of
        files that show analytics for the pipeline. It does this by creating a bash script, given above parameters, 
        running said script on the slurm cluster in a pre-existing virtual environment. This is the endpoint of a
        single image processing.
        
        :return: Returns a path to the output directory.
        """

        # Parameters to input to bash script template.
        script_config = {
            'filelist_path': str(self.filelist_path),
            'output_dir': str(self.working_dir / 'cell_profiler_outputs')
            'pipeline_path': str(self.cellprofiler_pipeline_path)
        }

        # Generates script_body from existing templates.
        jinja_env = Environment(loader=PackageLoader(package_name = 'celigo_image_core', package_path= 'templates'))
        # jinja_env = Environment(loader=FileSystemLoader('/allen/aics/microscopy/brian_whitney/templates'))
        script_body = jinja_env.get_template('cellprofiler_template.j2').render(script_config)

        # Creates bash script locally.
        with open(self.working_dir / 'cellprofiler.sh', 'w+') as rsh:
            rsh.write(script_body)

        # Runs cellprofiler on slurm
        subprocess.run(['sbatch', f'{str(self.working_dir)}/cellprofiler.sh'], check = True)

        # Returns path to directory of cellprofiler outputs
        self.cell_profiler_output_path =  self.working_dir / 'cell_profiler_outputs'


    def cleanup(self):
            shutil.rmtree(self.working_dir)