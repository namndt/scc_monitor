from datetime import datetime
from time import sleep
import servicemanager
import requests
import logging
import sys
import hpilo

from log_utility import ConfigLogger
from service_base import ServiceBase
from config_utility import INIConfiguration


# Declare global variable
LINE_NOTIFY_API_URL = 'http://10.199.15.109:8080/api/line/notify.php'
LINE_TOKEN: str
INTERVAL_TIME: int
ILO_HOST: str
ILO_LOGIN: str
ILO_PASSWORD: str
# For logger
logger: logging.Logger


class LINENotification():
    def send_notify(self, message: str):
        logger.debug(f'LINE message \"{message}\"')
        data = {'token': LINE_TOKEN, 'message': message}
        try:
            response = requests.post(url=LINE_NOTIFY_API_URL, data=data)
            logger.info(f'POST {LINE_NOTIFY_API_URL} {response.status_code} \"{response.message}\"')
        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def readable_format(self, disk_info) -> str:
        message = 'ASIS Data Server Disk is Failure\n' \
            '[Disk Name]: {0.p_Name}\n' \
            '[Status]: {0.p_Status}\n' \
            '[State]: {0.p_State}\n' \
            '[Event ID]: {0.p_EventID}\n'.format(disk_info)
        return message


class HPiLO_Monitor():
    _mailer = LINENotification()

    def server_health(self):
        try:
            ilo = hpilo.Ilo(hostname=ILO_HOST, login=ILO_LOGIN, password=ILO_PASSWORD)
            server_health_info_dict = ilo.get_embedded_health()
            fans_info_dict = server_health_info_dict['fans']
            temperature_info_dict = server_health_info_dict['temperature']
            power_supplies_dict = server_health_info_dict['power_supplies']
            power_supply_summary = server_health_info_dict['power_supply_summary']
        except Exception as ex:
            logger.exception(ex)

    def SaveToLog(self, disk):
        try:
            bad_disk_info = dict()
            bad_disk_info['id'] = disk.p_ID
            bad_disk_info['name'] = disk.p_Name
            bad_disk_info['status'] = disk.p_Status
            bad_disk_info['state'] = disk.p_State
            bad_disk_info['power_status'] = disk.p_PowerStatus
            bad_disk_info['failure_predicted'] = disk.p_EventID
            bad_disk_info['part_number'] = disk.p_PartNumber
            logger.warning(bad_disk_info)
        except AttributeError:
            logger.exception('Attribute not exist')


class Disk_Properties():
    p_ID: str
    p_Status: str
    p_Name: str
    p_State: str
    p_PowerStatus: str
    p_EventID: str
    p_PartNumber: str


class SCCService(ServiceBase):
    # Define service information
    _svc_name_ = 'SCCMonitor'
    _svc_display_name_ = 'SCC Health Monitor'
    _svc_description_ = 'SCC health monitor, possibly send LINE notify to L2 member group'

    def __init__(self, args):
        super().__init__(args)
        self._mailer = LINENotification()
        self._is_service_run = False

    def Inform_Log(self):
        logger.debug('=' * 80)
        logger.debug('service name: {}'.format(self._svc_name_))
        logger.debug('display name: {}'.format(self._svc_display_name_))
        logger.debug('description : {}'.format(self._svc_description_))
        logger.debug('=' * 80)

    # def isReportTime(self):
    #     try:
    #         current_time = datetime.now().time().strftime('%H:%M')
    #         expected_time = datetime.strptime(REPORT_TIME, '%H:%M').time().strftime('%H:%M')

    #         if current_time == expected_time:
    #             return True
    #         else:
    #             return False
    #     except Exception as ex:
    #         logger.exception(ex.args)

    def start(self):
        apply_config()
        self.Inform_Log()
        self._is_service_run = True
        logger.debug(f'Starting service {self._svc_name_}')
        self._mailer.send_notify(f'Starting service {self._svc_name_}')

    def stop(self):
        self._is_service_run = False
        logger.critical(f'Stopping service {self._svc_name_}')
        self._mailer.send_notify(f'Stopping service {self._svc_name_}')

    def main(self):
        try:
            disk_carer = HPiLO_Monitor()
            while self._is_service_run:
                disk_carer.server_health()
                sleep(60)
        except Exception as ex:
            logger.exception(ex.args)


def apply_config():
    logger.debug('=' * 32 + 'APPLY INI CONFIG' + '=' * 32)

    global LINE_TOKEN
    global INTERVAL_TIME
    global ILO_HOST
    global ILO_LOGIN
    global ILO_PASSWORD

    config = INIConfiguration()
    try:
        LINE_TOKEN = config.read('LINE_NOTIFY', 'line_token')
        INTERVAL_TIME = int(config.read('SETTING', 'monitoring_interval_in_seconds'))
        ILO_HOST = config.read('SETTING', '_ilo_host')
        ILO_LOGIN = config.read('SETTING', '_ilo_username')
        ILO_PASSWORD = config.read('SETTING', '_ilo_password')
    except Exception as e:
        logger.exception(e)

    logger.debug(f'LINE TOKEN: {LINE_TOKEN}')
    logger.debug(f'iLO connection setting: {ILO_HOST} {ILO_LOGIN} {ILO_PASSWORD}')


if __name__ == '__main__':
    # For config logging
    ConfigLogger()
    logger = logging.getLogger(__name__)

    if len(sys.argv) == 1:  # by pass error 1503
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SCCService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        SCCService.parse_command_line(SCCService)
