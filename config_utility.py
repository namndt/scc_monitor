from sys import executable
import os.path
from configparser import ConfigParser


class INIConfiguration():
    INI_FILE_NAME = 'scc_storage_monitor.ini'
    EXECUTEABLE_PATH = os.path.dirname(executable)
    INI_FILE_FULL_PATH = os.path.join(EXECUTEABLE_PATH, INI_FILE_NAME)

    def __init__(self):
        self.__config = ConfigParser()
        isExisting = os.path.isfile(self.INI_FILE_FULL_PATH)
        if isExisting is False:
            self.create_ini_file()

    def read(self, section, key):
        self.__config.read(self.INI_FILE_FULL_PATH)
        value = self.__config.get(section=section, option=key)
        return value

    def create_ini_file(self):
        self.__config = ConfigParser()
        self.__config['LINE_NOTIFY'] = {
            'line_token': 'RxO2huanbnu3H9xQoXlTiZXXvOOf5bUaqEcUvFnHMnP',
            'line_api_url': 'http://10.199.15.109:8080/api/line/notify.php'
        }
        self.__config['DATABASE'] = {
            'database_file_location': self.EXECUTEABLE_PATH,
            'database_file_name': 'SCC_STORAGE_MONITOR.DB',
            'keep_history_monitor_day': 7,
            'encryption_password': 'scc@123'
        }
        self.__config['ILO_SERVER'] = {
            'ilo_host': '192.168.152.46',
            'ilo_username': 'ilouser',
            'ilo_password': '12345678',
            'monitoring_interval_in_minute': '60'
        }
        self.__config['MSA_STORAGE'] = {
            'snmp_host_trap': '10.0.0.3'
        }

        with open(self.INI_FILE_FULL_PATH, mode='w') as configFile:
            self.__config.write(configFile)


if __name__ == "__main__":
    print('run config')
    config = INIConfiguration()
    print('ini file is existing: ' + os.path.isfile(config.INI_FILE_FULL_PATH).__str__())
    line_token = config.read('LINE_NOTIFY', 'line_token')
    interval = config.read('SETTING', 'om_report_time')
    print('line_token: ' + line_token)
    print('om_report_time: ' + interval)
