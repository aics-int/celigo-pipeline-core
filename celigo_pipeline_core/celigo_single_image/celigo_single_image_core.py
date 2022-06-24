import importlib.resources as pkg_resources
import os
from pathlib import Path
import pwd
import shutil
import subprocess

from aics_pipeline_uploaders import CeligoUploader
from jinja2 import Environment, PackageLoader
import pandas as pd

from .. import pipelines
from ..postgres_db_functions import add_to_table
from .celigo_image import CeligoImage


class CeligoSingleImageCore(CeligoImage):
    """This Class provides utility functions for the Celigo
    pipeline to prepare single celigo images.

    """

    def __init__(self, raw_image_path: str) -> None:
        """Constructor.

        Parameters
        ----------
        raw_image_path : str
            Raw celigo image path. This path is used to copy a version of the image to SLURM for
            processing.
        """

        # Directory Name, used to create working directory.
        self.tempdirname = Path(raw_image_path).with_suffix("").name

        # Working Directory Creation
        if not os.path.exists(
            f"/home/{pwd.getpwuid(os.getuid())[0]}/{self.tempdirname}"
        ):
            os.mkdir(f"/home/{pwd.getpwuid(os.getuid())[0]}/{self.tempdirname}")
        self.working_dir = Path(
            f"/home/{pwd.getpwuid(os.getuid())[0]}/{self.tempdirname}"
        )

        # Copying Image to working directory.
        self.raw_image_path = Path(raw_image_path)
        shutil.copyfile(
            self.raw_image_path, f"{self.working_dir}/{self.raw_image_path.name}"
        )
        self.image_path = Path(f"{self.working_dir}/{self.raw_image_path.name}")

        # Creating pipeline paths for templates
        with pkg_resources.path(pipelines, "rescale_pipeline.cppipe") as p:
            self.rescale_pipeline_path = p
        with pkg_resources.path(pipelines, "colonymorphology.model") as p:
            self.classification_model_path = p

        # Creating template for 96 well processing
        script_config = {
            "classifier_path": str(self.classification_model_path.parent),
        }
        jinja_env = Environment(
            loader=PackageLoader(
                package_name="celigo_pipeline_core", package_path="templates"
            )
        )
        script_body = jinja_env.get_template("96_well_pipeline_v2_tempalate.j2").render(
            script_config
        )
        with open(self.working_dir / "96_well_colony_pipeline_v2.cppipe", "w+") as rsh:
            rsh.write(script_body)
        self.cellprofiler_pipeline_path = (
            self.working_dir / "96_well_colony_pipeline_v2.cppipe"
        )

    def downsample(self):
        """downsample raw images for higher processing speed and streamlining of
        later steps

        Returns
        -------
        tuple[int,pathlib.Path]
            A list of namedtuples, The first of which being the SLURM job ID and the second
            being the desired output Path.
        """

        # Generates filelist for resize pipeline
        with open(self.working_dir / "resize_filelist.txt", "w+") as rfl:
            rfl.write(str(self.image_path) + "\n")
        self.resize_filelist_path = self.working_dir / "resize_filelist.txt"

        # Defines variables for bash script
        script_config = {
            "memory": "6G",
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
        output = subprocess.run(
            ["sbatch", f"{str(self.working_dir)}/resize.sh"],
            check=True,
            capture_output=True,
        )

        # Sets path to resized image to image path for future use
        self.image_path = (
            self.image_path.parent
            / f"{self.image_path.with_suffix('').name}_rescale.tiff"
        )

        job_ID = int(output.stdout.decode("utf-8").split(" ")[-1][:-1])
        return job_ID, self.image_path

    def run_ilastik(self):
        """Applies the Ilastik Pipeline processing to the downsampled image to
        produce a Probability map of the prior image.

        Returns
        -------
        tuple[int,pathlib.Path]
            A list of namedtuples, The first of which being the SLURM job ID and the second
            being the desired output Path.
        """

        # Parameters to input to bash script template
        script_config = {
            "memory": "12G",
            "image_path": f"'{str( self.image_path)}'",
            "output_path": f"'{str(self.image_path.with_suffix(''))}_probabilities.tiff'",
        }

        # Generates script for SLURM submission from templates.
        jinja_env = Environment(
            loader=PackageLoader(
                package_name="celigo_pipeline_core", package_path="templates"
            )
        )
        script_body = jinja_env.get_template("ilastik_template.j2").render(
            script_config
        )
        with open(self.working_dir / "ilastik.sh", "w+") as rsh:
            rsh.write(script_body)

        # Submit bash script ilastik.sh on SLURM
        output = subprocess.run(
            ["sbatch", f"{str(self.working_dir)}/ilastik.sh"],
            check=True,
            capture_output=True,
        )

        # Creates filelist.txt
        with open(self.working_dir / "filelist.txt", "w+") as rfl:
            rfl.write(str(self.image_path) + "\n")
            rfl.write(str(self.image_path.with_suffix("")) + "_probabilities.tiff")

        self.filelist_path = self.working_dir / "filelist.txt"
        job_ID = int(output.stdout.decode("utf-8").split(" ")[-1][:-1])
        return job_ID, Path(f"{self.image_path.with_suffix('')}_probabilities.tiff")

    def run_cellprofiler(self):
        """Applies the Cell Profiler Pipeline processing to the downsampled image using the Ilastik
        probabilities to produce a outlined cell profile and a series of metrics

        Returns
        -------
        tuple[int,pathlib.Path]
            A list of namedtuples, The first of which being the SLURM job ID and the second
            being the desired output Path.
        """

        # Parameters to input to bash script template.
        script_config = {
            "filelist_path": str(self.filelist_path),
            "output_dir": str(self.working_dir / "cell_profiler_outputs"),
            "pipeline_path": str(self.cellprofiler_pipeline_path),
            "memory": "12G",
        }

        # Generates script for SLURM submission from templates.
        jinja_env = Environment(
            loader=PackageLoader(
                package_name="celigo_pipeline_core", package_path="templates"
            )
        )
        script_body = jinja_env.get_template("cellprofiler_template.j2").render(
            script_config
        )
        with open(self.working_dir / "cellprofiler.sh", "w+") as rsh:
            rsh.write(script_body)

        # Submit bash script cellprofiler.sh on SLURM
        output = subprocess.run(
            ["sbatch", f"{str(self.working_dir)}/cellprofiler.sh"],
            check=True,
            capture_output=True,
        )

        # Set output path
        self.cell_profiler_output_path = self.working_dir / "cell_profiler_outputs"

        # Splits job id int from output
        job_ID = int(output.stdout.decode("utf-8").split(" ")[-1][:-1])

        return (
            job_ID,
            [
                Path(
                    f"{script_config['output_dir']}/{self.image_path.with_suffix('').name}_outlines.png"
                ),
                Path(f"{script_config['output_dir']}/ColonyDATA.csv"),
                Path(f"{script_config['output_dir']}/ImageDATA.csv"),
                Path(
                    f"{script_config['output_dir']}/PoorMorphObjectDATA.csv"
                ),  # These will eventually have to be modular
            ],
        )

    def upload_metrics(self, conn, table: str) -> str:
        """Uploads the metrics from the cell profiler pipeline run and comnbines them with
        the Images Metadata. Then Uploads metrics to postgres database.

        Parameters
        ----------
        postgres_password: str
            To access the postgres database a password is needed.

        table_name: str = '"Celigo_96_Well_Data_Test"'
            There are many tables in the Microscopy DB. This parameter specifies which table
            to insert metrics into.

        Returns
        -------
        self.raw_image_path.name
            returns the original files name. This return is used to index 'table_name' in the
            future in order to insert additional metrics.
        """
        celigo_image = CeligoUploader(self.raw_image_path, file_type="temp")
        metadata = celigo_image.metadata["microscopy"]

        # Building Metric Output from Cellprofiler outputs
        ColonyDATA = pd.read_csv(self.cell_profiler_output_path / "ColonyDATA.csv")
        ImageDATA = pd.read_csv(self.cell_profiler_output_path / "ImageDATA.csv")

        # formatting
        ColonyDATA = ColonyDATA[
            ColonyDATA.columns.drop(list(ColonyDATA.filter(regex="Metadata")))
        ]
        ColonyDATA["Metadata_DateString"] = (
            metadata["celigo"]["scan_date"] + " " + metadata["celigo"]["scan_time"]
        )
        ColonyDATA["barcode"] = metadata["plate_barcode"]
        ColonyDATA["Metadata_Well"] = celigo_image.well
        ColonyDATA["Experiment ID"] = self.raw_image_path.name
        ColonyDATA["row"] = int(celigo_image.row) - 1
        ColonyDATA["col"] = int(celigo_image.col) - 1
        result = pd.merge(ColonyDATA, ImageDATA, how="left", on="ImageNumber")
        result = result.drop(columns=["ImageNumber"])

        add_to_table(conn, result, table)

        return self.raw_image_path.name
