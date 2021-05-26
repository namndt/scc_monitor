import requests
from hashlib import md5
import urllib3
import sys
import json
from datetime import datetime, timedelta
from xml.etree import ElementTree as eTree
from sqlite_db import SQLiteDB


class HPMSA_Monitor():
    def __init__(self, msa_login, msa_password, use_ssl=False, verify_ssl=False, api_ver=2) -> None:
        self.__msa_login = msa_login
        self.__msa_pw = msa_password
        self.__use_ssl = use_ssl
        self.__verify_ssl = verify_ssl
        self.__api_ver = api_ver
        self.__db = SQLiteDB()

    def create_db(self):
        sql_txt = """
        CREATE TABLE IF NOT EXISTS sessionkey_cache (
            dns_name TEXT NOT NULL,
            ip TEXT NOT NULL,
            proto TEXT NOT NULL,
            expired TEXT NOT NULL,
            skey TEXT NOT NULL DEFAULT 0,
            PRIMARY KEY (dns_name, ip, proto)
        )
        """
        self.__db.execute_sql(sql_txt)
        print('create database succsessful!!')

    def make_cred_hash(self):
        cred = '_'.join([self.__msa_login, self.__msa_pw])
        hashed = md5(cred.encode()).hexdigest()
        print(f'MSA connection hashed: {hashed}')
        return hashed

    def get_skey(self, msa, hashed_login, use_cache=True):
        """
        Get session key from HP MSA API and and print it.\n
        :param msa: MSA IP address and DNS name.
        :type msa: tuple
        :param hashed_login: Hashed with md5 login data.
        :type hashed_login: str
        :param use_cache: The function will try to save session key to disk.
        :type use_cache: bool
        :return: Session key or error code.
        :rtype: str
        """
        # Trying to use cached session key
        if use_cache:
            cur_timestamp = datetime.timestamp(datetime.utcnow())
            if not self.__use_ssl:  # http
                cache_data = self.__db.execute_sql('SELECT expired, skey FROM sessionkey_cache WHERE ip="{}" AND proto="http"'.format(msa[0]))
            else:
                cache_data = self.__db.execute_sql('SELECT expired,skey FROM sessionkey_cache WHERE dns_name="{}" AND IP ="{}" AND proto="https"'.format(msa[1], msa[0]))
            if cache_data is not None:
                cache_expired, cached_skey = cache_data
                if cur_timestamp < float(cache_expired):
                    return cached_skey
                else:
                    return self.get_skey(msa, hashed_login, use_cache=False)
            else:
                return self.get_skey(msa, hashed_login, use_cache=False)
        else:
            # Forming URL and trying to make GET query
            msa_conn = msa[1] if self.__verify_ssl else msa[0]
            url = '{}/api/login/{}'.format(msa_conn, hashed_login)
            ret_code, sessionkey, xml = self.query_xmlapi(url=url, sessionkey=None)

            # 1 - success, write sessionkey to DB and return it
            if ret_code == '1':
                expired = datetime.timestamp(datetime.utcnow() + timedelta(minutes=30))
                if not self.__use_ssl:
                    cache_data = self.__db.execute_sql(f'SELECT ip FROM sessionkey_cache WHERE ip = "{msa[0]}" AND proto="http"')
                    if cache_data is None:
                        self.__db.execute_sql(f'INSERT INTO sessionkey_cache VALUES ("{msa[1]}", "{msa[0]}", "http", "{expired}", "{sessionkey}")')
                    else:
                        self.__db.execute_sql(f'UPDATE sessionkey_cache SET skey="{sessionkey}", expired="{expired}" WHERE ip="{msa[0]}" AND proto="http"')
                else:
                    cache_data = self.__db.execute_sql(f'SELECT dns_name, ip FROM sessionkey_cache WHERE dns_name="{msa[1]}" AND ip="{msa[1]}" AND proto="https"')
                    if cache_data is None:
                        self.__db.execute_sql(f'INSERT INTO sessionkey_cache VALUES ("{msa[1]}", "{msa[0]}", "https", "{expired}", "{sessionkey}")')
                    else:
                        self.__db.execute_sql(f'UPDATE sessionkey_cache SET skey = "{sessionkey}", expired = "{expired}" WHERE dns_name="{msa[1]}" AND ip="{msa[0]}" AND proto="https"')
                return sessionkey
            # 2 - Authentication Unsuccessful, return "2"
            elif ret_code == '2':
                return ret_code

    def query_xmlapi(self, url, sessionkey):
        """
        Making HTTP(s) request to HP MSA XML API.

        :param url: URL to make GET request.
        :type url: str
        :param sessionkey: Session key to authorize.
        :type sessionkey: Union[str, None]
        :return: Tuple with return code, return description and etree object <xml.etree.ElementTree.Element>.
        :rtype: tuple
        """
        # Set file where we can find root CA
        ca_file = '/etc/pki/tls/certs/ca-bundle.crt'

        # Makes GET request to URL
        try:
            # Connection timeout in seconds (connection, read).
            timeout = (3, 10)
            full_url = 'https://' + url if self.__use_ssl else 'http://' + url
            headers = {'sessionKey': sessionkey} if self.__api_ver == 2 else {'Cookie': "wbiusername={}; wbisessionkey={}"}
            if self.__use_ssl:
                if self.__verify_ssl:
                    response = requests.get(full_url, headers=headers, verify=ca_file, timeout=timeout)
                else:
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    response = requests.get(full_url, headers=headers, verify=False, timeout=timeout)
            else:
                response = requests.get(full_url, headers=headers, timeout=timeout)
        except requests.exceptions.SSLError:
            raise SystemExit('ERROR: Cannot verify storage SSL Certificate.')
        except requests.exceptions.ConnectTimeout:
            raise SystemExit('ERROR: Timeout occurred!')
        except requests.exceptions.ConnectionError as e:
            raise SystemExit("ERROR: Cannot connect to storage {}.".format(e))

        # Reading data from server XML response
        try:
            response_xml = eTree.fromstring(response.content)
            return_code = response_xml.find("./OBJECT[@name='status']/PROPERTY[@name='return-code']").text
            return_response = response_xml.find("./OBJECT[@name='status']/PROPERTY[@name='response']").text

            return return_code, return_response, response_xml
        except (ValueError, AttributeError) as e:
            raise SystemExit("ERROR: Cannot parse XML. {}".format(e))

    def expand_dict(self, init_dict):
        """
        Expand dict keys to full names

        :param init_dict: Initial dict
        :type: dict
        :return: Dictionary with fully expanded key names
        :rtype: dict
        """

        # Match dict for print output in human readable format
        m = {
            'h': 'health', 's': 'status', 'ow': 'owner', 'owp': 'owner-preferred', 't': 'temperature',
            'ts': 'temperature-status', 'cj': 'current-job', 'poh': 'power-on-hours', 'rs': 'redundancy-status',
            'fw': 'firmware-version', 'sp': 'speed', 'ps': 'port-status', 'ss': 'sfp-status',
            'fh': 'flash-health', 'fs': 'flash-status', '12v': 'power-12v', '5v': 'power-5v',
            '33v': 'power-33v', '12i': 'power-12i', '5i': 'power-5i', 'io': 'iops', 'cpu': 'cpu-load',
            'cjp': 'current-job-completion'
        }

        result_dict = {}
        for compid, metrics in init_dict.items():
            h_metrics = {}
            for key in metrics.keys():
                h_metrics[m[key]] = metrics[key]
            result_dict[compid] = h_metrics
        return result_dict

    def get_full_json(self, msa, component, sessionkey, pretty=4, human=True):
        # Forming URL
        msa_conn = msa[1] if self.__verify_ssl else msa[0]
        url = '{strg}/api/show/{comp}'.format(strg=msa_conn, comp=component)

        # Making request to API
        resp_return_code, resp_description, xml = self.query_xmlapi(url, sessionkey)
        if resp_return_code != '0':
            raise SystemExit('ERROR: {rc} : {rd}'.format(rc=resp_return_code, rd=resp_description))
        # Processing XML
        all_components = {}
        if component == 'disks':
            for PROP in xml.findall("./OBJECT[@name='drive']"):
                # Processing main properties
                disk_location = PROP.find("./PROPERTY[@name='location']").text
                disk_health_num = PROP.find("./PROPERTY[@name='health-numeric']").text
                disk_full_data = {
                    "h": disk_health_num
                }

                # Processing advanced properties
                disk_ext = dict()
                disk_ext['t'] = PROP.find("./PROPERTY[@name='temperature-numeric']")
                disk_ext['ts'] = PROP.find("./PROPERTY[@name='temperature-status-numeric']")
                disk_ext['cj'] = PROP.find("./PROPERTY[@name='job-running-numeric']")
                disk_ext['poh'] = PROP.find("./PROPERTY[@name='power-on-hours']")
                for prop, value in disk_ext.items():
                    if value is not None:
                        disk_full_data[prop] = value.text
                all_components[disk_location] = disk_full_data
        # Transform dict keys to human readable format if '--human' argument is given
        if human:
            all_components = self.expand_dict(all_components)
        return json.dumps(all_components, separators=(',', ':'), indent=pretty)


if __name__ == '__main__':
    args = sys.argv
    msa_ip, msa_login, msa_pw = args[1], args[2], args[3]
    component = args[4]
    print(args)
    msa_conn = (msa_ip, msa_ip)
    hpmsa = HPMSA_Monitor(msa_login, msa_pw)
    hpmsa.create_db()
    skey = hpmsa.get_skey(msa_conn, hpmsa.make_cred_hash())
    print(hpmsa.get_full_json(msa_conn, 'disks', skey))
