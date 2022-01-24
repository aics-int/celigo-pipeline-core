import pathlib
import subprocess
import numpy
import typing
import pathlib
import os
import tempfile
from pathlib import Path
# Steps
#   1) Create temp folder on slurm node 
#   2) Copy Celigo Image to temp folder 

#   3) 4x Downsampling of Celigo image 

#   4) Run Ilastik on Celigo Image (Bash Script)
#    - (output) need to write out file list 

#   5) Run Cell Profiler on celigo image (Bash Script)

#       Example filelsit: "Z:\aics\microscopy\CellProfiler_4.1.3_Testing\InputImages\filelist.txt"
#       Headless Example: "Z:\aics\microscopy\CellProfiler_4.1.3_Testing\headless.txt"


# 1) need to paramterzie Ilastik cli
# 2) need to pass in diffrent Ilastik project files
# 3) need to generate temp folder on the slurm node that you are on 




# what needs to be uploaded : raw Celigo image (FMS), 
#                             PNG output of cellprofiler (FMS),
#                             output metrics (Decide where) postgress

class CeligoSingleImageCore:

# Output_dir is the temporary folder 

    def create_temp_folder(self) -> os.PathLike:
        return Path(tempfile.gettempdir())

    def copy_celigo_image(
        self,
        raw_image_path: os.PathLike,
        output_dir: os.PathLike
    ) -> os.PathLike:
        raise NotImplementedError("copy_celigo_image")

    def downsample(
        self,
        raw_image_path: os.PathLike,
        output_dir: os.PathLike,
        scale_factor: int
    ) -> os.PathLike:
        raise NotImplementedError("downsample")

    def run_ilastik(
        self,
        downsample_path: os.PathLike,
        output_dir: os.PathLike    
    ) -> os.PathLike:
        raise NotImplementedError("run_ilastik")

    def run_cellprofiler(
        self,
        filelist_path: os.PathLike,
        output_dir: os.PathLike    
    ) -> os.PathLike:
        raise NotImplementedError("run_cellprofiler")

    def delete_temp_folder(self):
        raise NotImplementedError("create_temp_folder")