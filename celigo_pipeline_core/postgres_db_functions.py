from datetime import date
import os

from dotenv import find_dotenv, load_dotenv
import pandas as pd
import psycopg2
import psycopg2.extras as extras


def add_FMS_IDs_to_SQL_table(
    metadata: dict,
    conn,
    index: str,
):
    """Provides wrapped process for Insertion of FMS IDS into Postgres Database. Throughout the Celigo pipeline there are a few files
    We want to preserve in FMS, after upload these files FMS ID's are recorded in the Microscopy DB.

    1) Original Image

    2) Ilastik Probabilities

    3) Cellprofiler Outlines

    Parameters
    ----------
    metadata: dict
        List of metadata in form [KEY] : [VALUE] to be inserted into database.
    postgres_password : str
        Password used to access Microscopy DB. (Contact Brian Whitney, Aditya Nath, Tyler Foster)
    index : str
        index defines the rows that the FMS ID's will be inserted into. In most cases this will be the Experiment ID,
        which is just the original filename.
    table: str = TABLE_NAME
        Name of table in Postgres Database intended for import. Default is chosen by DEVS given current DB status
    """

    # Connect to DB
    load_dotenv(find_dotenv())
    cursor = conn.cursor()
    # Submit Queries
    for key in metadata:
        query = f'UPDATE {os.getenv("CELIGO_METRICS_DB")} SET "{key}" = %s WHERE "Experiment ID" = %s;'
        try:
            cursor.execute(query, (metadata[key], index))
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            print("Error: %s" % error)
            conn.rollback()
            cursor.close()
            return 1

    cursor.close()


def add_to_table(conn, metadata: pd.DataFrame, table: str):
    """A companion function for upload_metrics. This function provides the utility to insert
    metrics.

    Parameters
    ----------
    conn
        A psycopg2 database connection.
    metadata : pd.DataFrame
        The intended data to be inserted. This table is usually formatted
        by the upload_metrics funciton.
    postgres_table : str
        The specific table you wish to insert metrics into. The table name
        needs to be within quotes inside the string in order to be processed
        correctly by the database.
    """
    metadata = metadata.add_suffix('"')
    metadata = metadata.add_prefix('"')
    tuples = [tuple(x) for x in metadata.to_numpy()]

    cols = ",".join(list(metadata.columns))
    # SQL query to execute
    query = "INSERT INTO %s(%s) VALUES %%s" % (table, cols)
    cursor = conn.cursor()
    try:
        extras.execute_values(cursor, query, tuples)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        conn.rollback()
        cursor.close()
        return 1
    cursor.close()


def get_report_data(date: date):
    load_dotenv(find_dotenv())
    conn = psycopg2.connect(
        database=os.getenv("MICROSCOPY_DB"),
        user=os.getenv("MICROSCOPY_DB_USER"),
        password=os.getenv("MICROSCOPY_DB_PASSWORD"),
        host=os.getenv("MICROSCOPY_DB_HOST"),
        port=os.getenv("MICROSCOPY_DB_PORT"),
    )
    cursor = conn.cursor()
    query = f'select * from {os.getenv("CELIGO_STATUS_DB")} where "Date" = %s'
    cursor.execute(query, (str(date),))
    records = cursor.fetchall()
    data = []
    for row in records:
        info = {
            "Name": row[1],
            "Status": row[2],
            "ID": row[5],
            "Error": row[6],
        }
        data.append(info)

    daily_run_data = pd.DataFrame(data)
    filename = f"celigo_daily_log {date.today()}.csv"

    return filename, daily_run_data
