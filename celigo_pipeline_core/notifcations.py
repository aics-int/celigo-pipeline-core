from datetime import date
import json
import os
import pwd

from dotenv import load_dotenv
from jinja2 import Environment, PackageLoader
import psycopg2
import slack

from .postgres_db_functions import get_report_data


def send_slack_notification_on_failure(file_name: str, error: str, env_vars: str):
    """A utility function for Celigo Orchestration. This function takes the current running file
    and the error from its failure and reports them to the celigo slack channel.
    Parameters
    ----------
    file_name: str
        Name of Celigo Image.
    error: str
        Error of failed Celigo Image.
    env_vars: str
        Path to a .env file containing database credentials. Default is set to users home directory.
    """
    load_dotenv(env_vars)

    script_config = {
        "date": date.today(),
        "filename": file_name,
        "error": error,
    }

    jinja_env = Environment(
        loader=PackageLoader(
            package_name="celigo_pipeline_core", package_path="templates/slack"
        )
    )

    message = jinja_env.get_template("celigo_failed_upload.j2").render(script_config)

    blocks = json.loads(message)
    client = slack.WebClient(token=os.getenv("CELIGO_SLACK_TOKEN"))
    client.chat_postMessage(channel="#celigo-pipeline", blocks=blocks)


def slack_day_report(
    day: date = date.today(),
    env_vars: str = f"/home/{pwd.getpwuid(os.getuid())[0]}/.env",
):
    """Function to send a report describing the outcomes of Celigo pipeline runs
    for a given day.

    Parameters
    ----------
    conn
        A psycopg2 database connection.
    day: date
        The specific date to look at. Default is set to today's date
    env_vars: str
        Path to a .env file containing database credentials. Default is set to users home directory.

    """
    load_dotenv(env_vars)

    # Check that all variables from .env are  present
    if (
        any(
            [
                os.getenv("MICROSCOPY_DB"),
                os.getenv("MICROSCOPY_DB_USER"),
                os.getenv("MICROSCOPY_DB_PASSWORD"),
                os.getenv("MICROSCOPY_DB_HOST"),
                os.getenv("MICROSCOPY_DB_PORT"),
                os.getenv("CELIGO_SLACK_TOKEN"),
                os.getenv("CELIGO_METRICS_DB"),
                os.getenv("CELIGO_STATUS_DB"),
                os.getenv("CELIGO_CHANNEL_NAME"),
            ]
        )
        == "None"
    ):
        raise EnvironmentError(
            "Environment variables were not loaded correctly. Try adding 'load_dotenv(find_dotenv())' to your script"
        )
    try:
        # Establish connection to database
        conn = psycopg2.connect(
            database=os.getenv("MICROSCOPY_DB"),
            user=os.getenv("MICROSCOPY_DB_USER"),
            password=os.getenv("MICROSCOPY_DB_PASSWORD"),
            host=os.getenv("MICROSCOPY_DB_HOST"),
            port=os.getenv("MICROSCOPY_DB_PORT"),
        )
    except Exception as e:
        print("Connection Error: " + str(e))

    filename, df = get_report_data(date=day, conn=conn)
    _ = df.to_csv(filename, index=False)

    script_config = {
        "date": day,
        "count": df["Status"].count(),
        "total_success": df[df["Status"] == "Complete"]["Status"].count(),
        "total_fails": df[df["Status"] == "Failed"]["Status"].count(),
    }

    jinja_env = Environment(
        loader=PackageLoader(
            package_name="celigo_pipeline_core", package_path="templates/slack"
        )
    )

    message = jinja_env.get_template("celigo_day_report.j2").render(script_config)
    blocks = json.loads(message)
    client = slack.WebClient(token=os.getenv("CELIGO_SLACK_TOKEN"))
    client.chat_postMessage(channel="#celigo-pipeline", blocks=blocks)
    client.files_upload(
        channels="#celigo-pipeline",
        filename=filename,
        file=open(filename, "rb"),
    )

    os.remove(filename)


def get_channel_emails(channel_id: str) -> list:
    """A companion function for sending status emails. Takes all credentials in a slack
    channel and returns a list of emils

    Parameters
    ----------
    channel_id: str
        The identification number for a given slack channel you want to pull emails from.

    Returns
    -------
    emails: list
        list of channel emails
    """
    client = slack.WebClient(token=os.getenv("CELIGO_SLACK_TOKEN"))
    result = dict(client.conversations_members(channel=channel_id))
    emails = []
    for user in result["members"]:
        info = dict(client.users_info(user=user))["data"]
        if "email" in info["user"]["profile"].keys():
            emails.append(info["user"]["profile"]["email"])
    return emails


"""
def email_daily_report_to_channel():
    emails = get_channel_emails(os.getenv("CELIGO_CHANNEL_ID"))
    filename, df = get_report_data(date.today())
    data = df.to_csv(filename, index=False)
    for email in emails:
        email_daily_report(
            receiver=email,
            report=filename,
            total=data["Status"].count(),
            success=data.value_counts()["Complete"],
            failed=data.value_counts()["Failed"],
        )
    os.remove(filename)
"""
