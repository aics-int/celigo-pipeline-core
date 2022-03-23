import importlib.resources as pkg_resources
import os
from pathlib import Path
import shutil
import subprocess

from jinja2 import Environment, PackageLoader

from . import pipelines


class CeligoSingleImageCore:

    """
    This Class provides utility functions for the Celigo
    pipeline to prepare single images for:

    1) Ilastik Processing

    2) Cell Profiler Processing

    Given its large processing needs it is set up to run on slurm

    """

    def __init__(self, raw_image_path):

        # Specific name of experiment
        self.tempdirname = Path(raw_image_path).with_suffix("").name

        # Working Directory
        if not os.path.exists(
            f"/home/brian.whitney/{self.tempdirname}" #TODO: CHANGE TO HOME/USER
        ):  # NEEDS TO CHANGE TO HOME/USER
            os.mkdir(
                f"/home/brian.whitney/{self.tempdirname}" # TODO: CHANGE TO HOME/USER
            )  # NEEDS TO CHANGE TO HOME/USER
        # self.temp_dir = tempfile.TemporaryDirectory(dir='~/')
        self.working_dir = Path(
            f"/home/brian.whitney/{self.tempdirname}" #TODO: CHANGE TO HOME/USER
        )  # NEEDS TO CHANGE TO HOME/USER

        # Image Paths
        self.raw_image_path = Path(raw_image_path)
        shutil.copyfile(
            self.raw_image_path, f"{self.working_dir}/{self.raw_image_path.name}"
        )
        self.image_path = Path(f"{self.working_dir}/{self.raw_image_path.name}")

        # Future resource paths
        self.filelist_path = Path()
        self.resize_filelist_path = Path()
        self.cell_profiler_output_path = Path()

        # Pipeline paths for templates
        with pkg_resources.path(pipelines, "rescale_pipeline.cppipe") as p:
            self.rescale_pipeline_path = p
        with pkg_resources.path(pipelines, "96_well_colony_pipeline.cppipe") as p:
            self.cellprofiler_pipeline_path = p

    def downsample(self):
        # Generates a filelist
        with open(self.working_dir / "resize_filelist.txt", "w+") as rfl:
            rfl.write(str(self.image_path) + "\n")

        self.resize_filelist_path = self.working_dir / "resize_filelist.txt"

        # Defines variables for bash script
        script_config = {
            "filelist_path": str(self.resize_filelist_path),
            "output_path": str(self.working_dir),
            "pipeline_path": str(self.rescale_pipeline_path),
        }

        # Generates script_body from existing templates.
        jinja_env = Environment(
            loader=PackageLoader(
                package_name="celigo_pipeline_core", package_path="templates"
            )
        )
        script_body = jinja_env.get_template("resize_cellprofiler_template.j2").render(
            script_config
        )

        # Creates bash script locally.
        with open(self.working_dir / "resize.sh", "w+") as rsh:
            rsh.write(script_body)

        # Runs resize on slurm
        subprocess.run(["sbatch", f"{str(self.working_dir)}/resize.sh"], check=True)

        # Sets path to resized image to image path for future use
        self.image_path = (
            self.image_path.parent
            / f"{self.image_path.with_suffix('').name}_rescale.tiff"
        )

    def run_ilastik(self):

        # Parameters to input to bash script template
        script_config = {
            "image_path": f"'{str( self.image_path)}'",
            "output_path": f"'{str(self.image_path.with_suffix(''))}_probabilities.tiff'",
        }

        # Generates script_body from existing templates.
        jinja_env = Environment(
            loader=PackageLoader(
                package_name="celigo_pipeline_core", package_path="templates"
            )
        )

        script_body = jinja_env.get_template("ilastik_template.j2").render(
            script_config
        )

        # Creates bash script locally.
        with open(self.working_dir / "ilastik.sh", "w+") as rsh:
            rsh.write(script_body)

        # Runs ilastik on slurm
        subprocess.run(["sbatch", f"{str(self.working_dir)}/ilastik.sh"], check=True)

        # Creates filelist.txt
        with open(self.working_dir / "filelist.txt", "w+") as rfl:
            rfl.write(str(self.image_path) + "\n")
            rfl.write(str(self.image_path.with_suffix("")) + "_probabilities.tiff")

        self.filelist_path = self.working_dir / "filelist.txt"

    def run_cellprofiler(self):

        # Parameters to input to bash script template.
        script_config = {
            "filelist_path": str(self.filelist_path),
            "output_dir": str(self.working_dir / "cell_profiler_outputs"),
            "pipeline_path": str(self.cellprofiler_pipeline_path),
        }

        # Generates script_body from existing templates.
        jinja_env = Environment(
            loader=PackageLoader(
                package_name="celigo_pipeline_core", package_path="templates"
            )
        )
        script_body = jinja_env.get_template("cellprofiler_template.j2").render(
            script_config
        )

        # Creates bash script locally.
        with open(self.working_dir / "cellprofiler.sh", "w+") as rsh:
            rsh.write(script_body)

        # Runs cellprofiler on slurm
        subprocess.run(
            ["sbatch", f"{str(self.working_dir)}/cellprofiler.sh"], check=True
        )

        # Returns path to directory of cellprofiler outputs
        self.cell_profiler_output_path = self.working_dir / "cell_profiler_outputs"

    def cleanup(self):
        shutil.rmtree(self.working_dir)
