from datetime import date
import json
import os

from dotenv import find_dotenv, load_dotenv
from jinja2 import Environment, PackageLoader
import slack

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

    script_config = {}

    jinja_env = Environment(
        loader=PackageLoader(
            package_name="celigo_pipeline_core", package_path="templates/slack"
        )
    )

    message = jinja_env.get_template("celigo_day_report.j2").render(script_config)

    blocks = json.loads(message)
    client = slack.WebClient(token=os.getenv("CELIGO_SLACK_TOKEN"))
    client.chat_postMessage(channel="#celigo-pipeline", blocks=blocks)


"""
def email_day_report():

def get_emails():

    load_dotenv(find_dotenv())
    channel_list = requests.get('https://slack.com/api/groups.list?token=%s' % os.getenv("CELIGO_SLACK_TOKEN")).json()['groups']
    channel = filter(lambda c: c['name'] == os.getenv("CELIGO_CHANNEL_NAME:"), channel_list)[0]

    members = requests.get('https://slack.com/api/conversations.members?token=%s&channel=%s' % (os.getenv("CELIGO_SLACK_TOKEN"), channel['id'])).json()['members']

    users_list = requests.get('https://slack.com/api/users.list?token=%s' % os.getenv("CELIGO_SLACK_TOKEN")).json()['members']

    for user in users_list:
        if "email" in user['profile'] and user['id'] in members:
            print(user['profile']['email'])

"""
