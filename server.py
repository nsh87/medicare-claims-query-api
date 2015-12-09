from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import locale
import os

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify

import re

re.sub

from core.utilities import cursor_connect
from db import config as dbconfig

app = Flask(__name__)

TABLE_NAME = dbconfig.db_tablename

locale.setlocale(locale.LC_ALL, '')  # For formatting numbers with commas

# Default to connect to production environment, override later if dev server
try:
    db_dsn = "host={0} dbname={1} user={2} password={3}".format(
        dbconfig.rds_dbhost, dbconfig.rds_dbname, dbconfig.rds_dbuser,
        dbconfig.rds_dbpass)
except ValueError:
    pass


def json_error(code, err):
    """
    Make a JSON error response.

    Parameters
    ----------
    code : int
        The HTTP error code to return.
    err : str
        Error message to return as JSON.

    Returns
    -------
    response
        A JSON response.
    """
    response = jsonify(error=err)
    response.status_code = code
    return response


@app.route('/')
def index():
    """
    Main page with no JSON API, just a short message about number of rows
    available.

    Returns
    -------
    str
        A short message saying hello and then displaying the number of rows
        available to query.
    """
    num_rows = 0  # Default value
    try:
        con, cur = cursor_connect(db_dsn)
        sql = "SELECT COUNT(*) FROM {0}".format(TABLE_NAME)
        cur.execute(sql)
        result = cur.fetchone()
        num_rows = int(result[0])
    except (psycopg2.Error, ValueError) as e:
        num_rows = 0
    finally:
        return "Hello World! I can access {0:,d} rows of data!".format(num_rows)


@app.route('/api/v1/count/<col>')
def get_counts(col):
    """
    Get counts of distinct values in the available columns.

    Returns
    -------
    json
        A labeled JSON object with corresponding counts.
    """
    count = {}
    cleaned_col = re.sub('\W+', '', col)
    try:
        if cleaned_col == 'id':
            return json_error(403,
                              "column '{0}' is not allowed".format(cleaned_col))
        con, cur = cursor_connect(db_dsn, psycopg2.extras.DictCursor)
        query = """
        SELECT {0}, COUNT(*) AS num FROM {1}
        GROUP BY {0};""".format(cleaned_col, TABLE_NAME)
        cur.execute(query, (cleaned_col, ))
        result = cur.fetchall()
        for row in result:
            label = row[cleaned_col]
            count[label] = row['num']
    except Exception as e:
        return jsonify({'error': e.message})
    return jsonify(count)

if __name__ == '__main__':
    # NOTE: anything you put here won't get picked up in production
    current_dir = os.path.dirname(os.path.realpath(__file__))
    if os.path.isfile(os.path.join(current_dir, 'PRODUCTION')):
        app.run()
    else:
        # Running dev server...
        db_dsn = "host={0} dbname={1} user={2}".format(dbconfig.vagrant_dbhost,
                                                       dbconfig.vagrant_dbname,
                                                       dbconfig.vagrant_dbuser)
        app.run(host='0.0.0.0', debug=True)
