"""
This module used for create SCC Monitor record history.\n
User can create SQLite database or Insert/Update/Delete table
"""
import sqlite3
import logging
from pathlib import Path, PurePath
from config_utility import INIConfiguration


class SQLiteDB():
    def __init__(self) -> None:
        self._db_file_path = self.get_db_dir()
        self._logger = logging.getLogger(__name__)

    def get_db_dir():
        _config = INIConfiguration()
        db_dir = _config.read('SQLite_DB', 'database_file_location')
        db_name = _config.read('SQLite_DB', 'database_file_name')
        Path(db_dir).mkdir(parents=False, exist_ok=True)
        return PurePath(db_dir).joinpath(db_name)

    def create_connection(self) -> sqlite3.Connection:
        try:
            _conn = None
            _conn = sqlite3.connect(self._db_file_path)
        except sqlite3.Error as e:
            self._logger.exception(e)
        finally:
            return _conn

    def create_table(self, conn: sqlite3.Connection):
        fans_table_sql = """
        CREATE TABLE IF NOT EXISTS cooling_fans (
            date_time TEXT NOT NULL,
            fan_bays TEXT NOT NULL,
            status   TEXT NOT NULL,
            speed_percentage REAL NOT NULL,
            is_alarmed INTEGER NOT NULL CHECK (is_alarmed IN (0, 1)) DEFAULT 0,
            is_sent_line INTEGER NOT NULL CHECK (is_sent_line IN (0, 1)) DEFAULT 0
        );
        """
        temperature_table_sql = """
        CREATE TABLE IF NOT EXISTS temperature (
            date_time TEXT NOT NULL,
            sensor_name TEXT NOT NULL,
            localtion TEXT NOT NULL,
            value REAL NOT NULL,
            status TEXT NOT NULL,
            is_alarmed INTEGER NOT NULL CHECK (is_alarmed IN (0, 1)) DEFAULT 0,
            is_sent_line INTEGER NOT NULL CHECK (is_sent_line IN (0, 1)) DEFAULT 0
        )
        """
        pw_table_sql = """
        CREATE TABLE IF NOT EXISTS power_supplies (
            date_time TEXT NOT NULL,
            pw_name TEXT NOT NULL,
            is_present INTEGER NOT NULL CHECK (is_present IN (0, 1)) DEFAULT 1,
            status   TEXT NOT NULL,
            current_pw REAL NOT NULL,
            pw_redundancy TEXT NOT NULL,
        )
        """
        storage_table_sql = """
        CREATE TABLE IF NOT EXISTS storage (
        )
        """
        sessionkey_cache_sql = """
        CREATE TABLE IF NOT EXISTS sessionkey_cache (
            'dns_name TEXT NOT NULL,
            'ip TEXT NOT NULL,
            'proto TEXT NOT NULL,
            'expired TEXT NOT NULL,
            'skey TEXT NOT NULL DEFAULT 0,
            'PRIMARY KEY (dns_name, ip, proto)
        )
        """
        __cursor = conn.cursor()
        __cursor.execute(fans_table_sql)

    def execute_sql(self, query, fetch_all=False):
        """
        Check and execute SQL query.\n
        :param query: SQL query to execute.
        :type query: str
        :param fetch_all: Set it True to execute fetchall().
        :type fetch_all: bool
        :return: Tuple with SQL query result.
        :rtype: tuple
        """
        conn = self.create_connection()
        data = "No data"
        if conn:
            cursor = conn.cursor()
            try:
                if not fetch_all:
                    data = cursor.execute(query).fetchone()
                else:
                    data = cursor.execute(query).fetchall()
            except sqlite3.OperationalError as e:
                self._logger.exception(f'{e}. Query: {query}')
            conn.commit()
            conn.close()
            return data
        else:
            self._logger.error(f'Cannot create connection to {self._db_file_path}')


if __name__ == '__main__':
    db_dir = 'D:\\SVN_WorkingDir\\scc_monitor\\database'
    db_name = 'test.db'
    Path(db_dir).mkdir(parents=False, exist_ok=True)
    print(PurePath(db_dir).joinpath(db_name))
