#!/bin/bash
#SBATCH --time=9-24:00:00
#SBATCH --partition=aics_cpu_general
#SBATCH --mem=50G
#activate Conda
. /allen/aics/apps/prod/anaconda/Anaconda3-5.1.0/bin/activate
#activate Ilastik conda environment
conda activate /allen/aics/apps/prod/venvs/cellprofiler/v4.1.3



