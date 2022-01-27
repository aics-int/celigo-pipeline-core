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

        # Creates a bash script to run Ilastik and output a probability map
        with open (self.working_dir / 'ilastik.sh', 'w') as rsh:
            rsh.write(f'''#!/bin/bash
        #SBATCH --time=9-24:00:00
        #SBATCH --partition=aics_cpu_general
        #SBATCH --mem=50G

        # activate Conda
        . /allen/aics/apps/prod/anaconda/Anaconda3-5.1.0/bin/activate

        # activate Ilastik conda environment
        conda activate /allen/aics/apps/prod/venvs/cellprofiler/v4.1.3

        # run Ilastik
        /allen/aics/apps/prod/ilastik/ilastik-1.3.3post3-Linux/run_ilastik.sh 
        --headless 
        --project="/allen/aics/microscopy/CellProfiler_4.1.3_Testing/ballingandlifting.ilp" 
        --output_format=tiff 
        --export_source="Probabilities" 
        --raw_data {str(self.image_path)}
        --output_filename_format={str(self.working_dir)}/{{nickname}}_probabilities.tiff ''')

        # This will change to submission to slurm
        subprocess.call(self.working_dir / 'ilastik.sh')

        # Creates filelist.txt file with the path to the downsampled image 
        # and the path to the probability map. This file (filelist.txt) is needed
        # for filelist_path for run_cellprofiler
        with open(self.working_dir / 'filelist.txt', 'w') as rfl:
            rfl.write(str(self.image_path))
            rfl.write(str(self.image_path.parent / f"{self.image_path.with_suffix('').with_suffix('').name}_probabilities.tiff"))

        # returns path to filelist 
        self.filelist = self.working_dir / 'filelist.txt'

    def run_cellprofiler(self) -> Path:

        """
        FUNCTIONALITY: This method takes aa path to a filelist.txt file and creates a directory with a myriad of
        files that show analytics for the pipeline. It does this by creating a bash script, given above parameters, 
        running said script on the slurm cluster in a pre-existing virtual environment. This is the endpoint of a
        single image processing.
        
        :return: Returns a path to the output directory.
        """

        # Creates a bash script to run CellProfiler and output a directory of analytics
        with open(self.working_dir / 'cellprofiler.sh', 'w') as rsh:
            rsh.write(f'''#!/bin/bash
        #SBATCH --time=9-24:00:00
        #SBATCH --partition=aics_cpu_general
        #SBATCH --mem=50G

        # activate Conda
        . /allen/aics/apps/prod/anaconda/Anaconda3-5.1.0/bin/activate

        # activate cellprofiler conda environment
        conda activate /allen/aics/apps/prod/venvs/cellprofiler/v4.1.3
        
        # run CellProfiler
        cellprofiler -r -c -p /allen/aics/microscopy/CellProfiler_4.1.3_Testing/96_well_colony_pipeline.cppipe
        --file-list = {str(self.filelist_path)} 
        -o {str(self.working_dir / 'cell_profiler_outputs')}''')

        #This will change to submission to slurm
        subprocess.call(self.working_dir / 'cellprofiler.sh')

        return self.working_dir / 'cell_profiler_outputs'
        