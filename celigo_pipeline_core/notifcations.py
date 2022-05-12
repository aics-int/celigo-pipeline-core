from datetime import date
import json
import os

from dotenv import find_dotenv, load_dotenv
from jinja2 import Environment, PackageLoader
import slack

from .postgres_db_functions import get_report_data

# import requests


def send_slack_notification_on_failure(file_name: str, error: str):

    load_dotenv(find_dotenv())

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


def slack_day_report():

    load_dotenv(find_dotenv())
    filename, df = get_report_data(date.today())
    data = df.to_csv(filename, index=False)

    script_config = {
        "date": date.today(),
        "count": data["Status"].count(),
        "total_success": data.value_counts()["Complete"],
        "total_fails": data.value_counts()["Failed"],
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
    client = slack.WebClient(token=os.getenv("CELIGO_SLACK_TOKEN"))
    result = client.conversations_members(channel=channel_id)
    emails = []
    for user in result["members"]:
        info = client.users_info(user=user).data
        if "email" in info["user"]["profile"].keys():
            emails.append(info["user"]["profile"]["email"])
    return emails

'''
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
'''