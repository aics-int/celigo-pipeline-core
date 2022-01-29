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
    This Class provides utility functions for the Celigo pipeline to prepare single images for:

    1) Ilastik Processing

    2) Cell Profiler Processing

    """

    filelist = Path('') # I am not sure if this is the correct initialzation for this 

    def __init__(self, raw_image_path):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.working_dir = Path(self.temp_dir.name)
        shutil.copyfile(raw_image_path, f'{self.working_dir}/{raw_image_path.name}')
        self.image_path =  Path(f'{self.working_dir}/{raw_image_path.name}')


    def downsample(self, scale_factor: int):
        """
        PARAMETERS: Takes in a scaling factor (scale_factor).
        
        FUNCTIONALITY: This method takes an existing image and creates a copy of the image scaled by a given 
        quantity/magnification. Ex. 4 --> 1/4 size.
        
        :return: Returns a path to the resized image.
        """

        image = AICSImage(self.image_path)
        image_rescaled = rescale(image.get_image_data(), 1 / scale_factor, anti_aliasing=False)
        image_rescaled_path = self.image_path.parent / f"{self.image_path.with_suffix('').name}_rescale.ome.tiff"
        OmeTiffWriter.save(image_rescaled, image_rescaled_path, dim_order= image.dims.order)
        self.image_path = image_rescaled_path


    def run_ilastik(self):

        """
        FUNCTIONALITY: This method takes an existing image either scaled or unscaled and creates a probability 
        map of [I DON'T KNOW]. It does this by creating a bash script, given above parameters, running said script 
        on the slurm cluster in a pre-existing virtual environment and then generating a list of pertinent files
        called filelist.txt (containing the path to the image and to the probability map). This file is necessary
        to run CellProfiler.
        
        :return: Returns a path to the filelist.
        """
        # Parameters to input to bash script template 
        script_config = {
            'image_path': str(self.image_path),
            'output_name': str(self.image_path / '_probabilities.tiff')
        }

        # Generates script_body from existing templates.
        jinja_env = Environment(loader=FileSystemLoader('Z:/aics/microscopy/brian_whitney/templates'))
        script_body = jinja_env.get_template('ilastik_template.j2').render(script_config)

        # Creates bash script locally.
        with open(self.working_dir / 'run_ilastik.sh', 'w') as rsh:
            rsh.write(script_body)

        # Runs ilastik on slurm
        subprocess.run(['sbatch', f'{str(self.working_dir)}/run_cellprofiler.sh'], check = True)

        # Creates filelist.txt
        with open(self.working_dir / 'filelist.txt', 'w') as rfl:
            rfl.write(str(self.image_path))
            rfl.write(str(self.image_path.parent / f"{self.image_path.with_suffix('').with_suffix('').name}_probabilities.tiff"))

        self.filelist = self.working_dir / 'filelist.txt'

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
            'filelist_path': str(self.filelist),
            'output_dir': str(self.working_dir / 'cell_profiler_outputs')
        }

        # Generates script_body from existing templates.
        jinja_env = Environment(loader=FileSystemLoader('Z:/aics/microscopy/brian_whitney/templates'))
        script_body = jinja_env.get_template('cellprofiler_template.j2').render(script_config)

        # Creates bash script locally.
        with open(self.working_dir / 'run_cellprofiler.sh', 'w') as rsh:
            rsh.write(script_body)

        # Runs cellprofiler on slurm
        subprocess.run(['sbatch', f'{str(self.working_dir)}/run_cellprofiler.sh'], check = True)

        # Returns path to directory of cellprofiler outputs
        return self.working_dir / 'cell_profiler_outputs'
        