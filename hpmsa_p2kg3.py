from hashlib import md5
import os
from datetime import datetime, timedelta

import requests
import sqlite3


CACHE_DB = ''


def init_skey_cache(cache_dir):
    try:
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir, mode=0o755)
    except PermissionError as e:
        raise SystemExit(f'ERROR: You don\'t have permission to create {cache_dir} directoty')
    # Init cache database
    if not os.path.exists(CACHE_DB):
        session_key_table_sql = '''
        CREATE TABLE IF NOT EXISTS skey_cache (
            dns_name TEXT NOT NULL,
            ip TEXT NOT NULL,
            proto TEXT NOT NULL,
            expired TEXT NOT NULL,
            skey TEXT NOT NULL DEFAULT 0,
            PRIMARY KEY (dns_name, ip, proto)
        )'
        '''

        os.chmod(CACHE_DB, 0o664)
        print("Cache database initialized as: '{}'".format(CACHE_DB))


def sql_cmd(query, fetch_all=False):
    """
    Check and execute SQL query.

    :param query: SQL query to execute.
    :type query: str
    :param fetch_all: Set it True to execute fetchall().
    :type fetch_all: bool
    :return: Tuple with SQL query result.
    :rtype: tuple
    """

    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        try:
            if not fetch_all:
                data = cursor.execute(query).fetchone()
            else:
                data = cursor.execute(query).fetchall()
        except sqlite3.OperationalError as e:
            if str(e).startswith('no such table'):
                raise SystemExit("Cache is empty")
            else:
                raise SystemExit('ERROR: {}. Query: {}'.format(e, query))
        conn.commit()
        conn.close()
        return data
    except sqlite3.OperationalError as e:
        print("CACHE ERROR: (db: {}) {}".format(CACHE_DB, e))
