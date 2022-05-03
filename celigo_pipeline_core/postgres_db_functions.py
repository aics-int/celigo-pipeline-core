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
