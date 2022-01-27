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

# Output_dir is the temporary folder 

    @staticmethod
    def create_temp_folder(
    ) -> Path:
        """
        PARAMETERS: None.
        
        FUNCTIONALITY: This method simply creates a temporary working directory. 
        
        :return: Returns a path to the temporary directory.
        
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
        return temp_dir_path

    @staticmethod
    def copy_celigo_image(
        raw_image_path: Path,
        output_dir: Path
    ) -> Path:
        """
        PARAMETERS: Takes in a path to a directory (raw_image_path) to copy from path to a directory to 
        paste to (output_dir).
        
        FUNCTIONALITY: This method takes an existing image at a given location and clones it to 
        somewhere else.
        
        :return: Returns a path to the cloned image.
        """

        shutil.copyfile(raw_image_path, f'{output_dir}/{raw_image_path.name}')
        return Path(f'{output_dir}/{raw_image_path.name}')
 

    @staticmethod
    def downsample(
        image_path: Path,
        scale_factor: int
    ) -> Path:
        """
        PARAMETERS: Takes in a path to an image (image_path) and a scaling factor (scale_factor).
        
        FUNCTIONALITY: This method takes an existing image and creates a copy of the image scaled by a given 
        quantity/magnification. Ex. 4 --> 1/4 size.
        
        :return: Returns a path to the resized image.
        """

        image = AICSImage(image_path)
        image_rescaled = rescale(image.get_image_data(), 1 / scale_factor, anti_aliasing=False)
        image_rescaled_path = image_path.parent / f"{image_path.with_suffix('').name}_rescale.ome.tiff"
        OmeTiffWriter.save(image_rescaled, image_rescaled_path, dim_order= image.dims.order)
        return image_rescaled_path


    @staticmethod
    def run_ilastik(
        image_path: Path,
        output_dir: Path    
    ) -> Path:
        """
        PARAMETERS: Takes in a path to an image (image_path) and an output directory (output_dir).
        
        FUNCTIONALITY: This method takes an existing image either scaled or unscaled and creates a probability 
        map of [I DON'T KNOW]. It does this by creating a bash script, given above parameters, running said script 
        on the slurm cluster in a pre-existing virtual environment and then generating a list of pertinent files
        called filelist.txt (containing the path to the image and to the probability map). This file is necessary
        to run CellProfiler.
        
        :return: Returns a path to the filelist.
        """

        # Creates a bash script to run Ilastik and output a probability map
        with open (output_dir / 'ilastik.sh', 'w') as rsh:
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
        --raw_data {str(image_path)}
        --output_filename_format={str(output_dir)}/{{nickname}}_probabilities.tiff ''')

        # This will change to submission to slurm
        subprocess.call(output_dir / 'ilastik.sh')

        # Creates filelist.txt file with the path to the downsampled image 
        # and the path to the probability map. This file (filelist.txt) is needed
        # for filelist_path for run_cellprofiler
        with open(output_dir / 'filelist.txt', 'w') as rfl:
            rfl.write(str(image_path))
            rfl.write(str(image_path.parent / f"{image_path.with_suffix('').with_suffix('').name}_probabilities.tiff"))

        #returns path to filelist 
        return output_dir / 'filelist.txt'


    @staticmethod
    def run_cellprofiler(
        filelist_path: Path,
        output_dir: Path    
    ) -> Path:

        """
        PARAMETERS: Takes in a path to a filelist.txt file (filelist_path) and an output directory (output_dir).
        Output: Returns a path to the Resized Image 
        
        FUNCTIONALITY: This method takes aa path to a filelist.txt file and creates a directory with a myriad of
        files that show analytics for the pipeline. It does this by creating a bash script, given above parameters, 
        running said script on the slurm cluster in a pre-existing virtual environment. This is the endpoint of a
        single image processing.
        
        :return: Returns a path to the output directory.
        """

        # Creates a bash script to run CellProfiler and output a directory of analytics
        with open(output_dir / 'cellprofiler.sh', 'w') as rsh:
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
        --file-list = {str(filelist_path)} 
        -o {str(output_dir / 'cell_profiler_outputs')}''')

        #This will change to submission to slurm
        subprocess.call(output_dir / 'cellprofiler.sh')

        return output_dir / 'cell_profiler_outputs'
        