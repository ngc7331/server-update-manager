'''
version 2022.02.20.1
'''

from appwrite.client import Client
from appwrite.services.database import Database
from appwrite.services.storage import Storage
import json
import logging
from modules.popen import popen
from modules.Logger import Logger
from modules.const import *
import os
import psutil
import sys
import time
import urllib3


def Green(msg:str) -> str:
    return '\033[32m%s\033[0m' % msg


class API():
    def __init__(self, conf:dict, logger:Logger=None) -> None:
        # Load conf
        self.name = conf['client_name']
        self._endpoint = conf['endpoint']
        self._project = conf['project']
        self._key = conf['key']
        self._collection_id = conf['collection']
        self._permission = conf['permission']
        self._logger = logger if logger is not None else Logger()
        self._status = None

        # Init Client, Database and Storage
        self._client = Client()
        self._client.set_endpoint(self._endpoint)\
            .set_project(self._project)\
            .set_key(self._key)
        self._database = Database(self._client)
        self._storage = Storage(self._client)

        # Get document id
        result = self._database.list_documents(self._collection_id)
        clients = {}
        for client in result['documents']:
            clients.update({client['name']: client['$id']})
        if (self.name in clients.keys()):
            self._document_id = clients[self.name]
            self._logger.info('Get document id: %s' % Green(self._document_id))
        else:
            self._document_id = None

    def post(self, data:dict):
        '''Post data to collection by update or create a document'''
        if 'time' not in data:
            data.update({'time': time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(time.time()))})
        if self._document_id is not None:
            return self._database.update_document(
                self._collection_id, self._document_id, data,
                self._permission, self._permission
            )
        else:
            data.update({'name': self.name})
            result = self._database.create_document(
                self._collection_id, 'unique()', data,
                self._permission, self._permission
            )
            self._document_id = result['$id']
            return result
    def remove(self):
        '''Remove document from collection'''
        if (self._document_id is None):
            return None
        result = self._database.delete_document(
            self._collection_id, self._document_id
        )
        self._document_id = None
        return result

    def init(self) -> None:
        self.post({
            'error': False,
            'status': INIT,
            'msg': ''
        })

    def status(self, status:int) -> None:
        self._logger.info('status {} -> {} post to api'.format(self._status, status))
        self._status = status
        self.post({'status': status})

    def error(self, msg:str) -> None:
        self.post({'error': True, 'msg': msg})
    def fatal(self, msg:str) -> None:
        self.post({'status': FATAL, 'error': True, 'msg': msg})

    def checkAuthorization(self) -> int:
        document = self._database.get_document(self._collection_id, self._document_id)
        return document['status']

    def upload(self, filepath:str):
        if (not os.path.exists(filepath)):
            return None
        return self._storage.create_file(
            'unique()', open(filepath, 'rb'),
            self._permission, self._permission
        )


def keyboardInterruptHandler() -> None:
    logger.info('Keyboard interrupt: ')
    input('To exit, press ctrl+c again; else, press enter.')


def waitUntil(check, target_status:int, logger:Logger,
              interval:float = 300, retries:int = 0, max_retries:int = 288) -> bool:
    if (retries > max_retries):
        return False
    status = check()
    if (status != target_status):
        logger.debug(f"status({status}) doesn't match target({target_status}), sleep {interval} seconds")
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            keyboardInterruptHandler()
        return waitUntil(check, target_status, logger, interval, retries+1, max_retries)
    return True


def checkLock() -> int:
    if not os.path.exists('system_update.lock'):
        return 0
    with open('system_update.lock', 'r') as f:
        pid = int(f.read())
    if pid not in psutil.pids():
        return 0
    if psutil.Process(pid).name() != 'python3':
        return 0
    return pid


def parseErr(msg: str) -> str:
    res = []
    for line in msg.splitlines():
        if (line.startswith('E:') or
            line.startswith('Err:') or
            line.startswith('W:') or
            line.startswith('Warn:')
        ): res.append(line)
    return '\n'.join(res)


def aptUpdate() -> bool:
    logger.info('apt update')
    api.status(PROC_UPDATE)
    popen('apt update > system_update.tmp 2>&1')
    with open('system_update.tmp', 'r') as f:
        result = f.read()
        logger.debug(result)
    err = parseErr(result)
    if (err):
        api.error(f'apt update completed with error:\n{err}')
        logger.error('apt update completed with error, trying to ignore')
        logger.warning(err)
    if('apt list --upgradable' not in result):
        return False

    logger.info('Get upgrade_list and hold_list')
    popen('apt list --upgradable > system_update.tmp')
    with open('system_update.tmp', 'r') as f:
        result = f.readlines()
    os.remove('system_update.tmp')
    hold_list = popen('apt-mark showhold').read().decode()

    logger.info(Green('Update found'))
    msg = ''
    for line in result:
        if ('正在列表' in line or 'Listing' in line):
            continue
        # line = '{prog}/{source} {newversion} {architecture} [upgradable from: {oldversion}]'
        prog = line.split('/')[0]
        progs.append(json.dumps({
            'name': prog,
            'hold': prog in hold_list,
            'version': [
                line.split(' ')[1], #新版本
                line.split(' ', 3)[3].replace('[可从该版本升级：','').replace('[upgradable from: ','').replace(']\n','') #旧版本
            ]
        }))
        line = '[Hold] %s' % line if (prog in hold_list) else line
        msg += line
    logger.info(msg)
    logger.info('Post API')
    result = api.post({
        'progs': progs,
        'status': AUTH_UPGRADE
    })
    document_id = result['$id']
    logger.debug(result)
    logger.info('Status posted to api, document id: %s' % Green(document_id))
    return True


def aptHold() -> None:
    logger.info('set apt hold')
    api.status(PROC_HOLD)
    hold_list = popen('apt-mark showhold').read().decode()
    for prog in progs:
        prog = json.loads(prog)
        if (prog['name'] in hold_list and not prog['hold']):
            logger.info('Unhold {name}, it will be upgraded from {version[1]} to {versiob[0]}'.format(**prog))
            popen('apt-mark unhold %s' % prog['name'])
        elif (prog['name'] not in hold_list and prog['hold']):
            logger.info('Hold {name} at version {version[1]}'.format(**prog))
            popen('apt-mark hold %s' % prog['name'])
    api.status(WAIT_UPGRADE)


def aptUpgrade() -> bool:
    logger.info('apt upgrade')
    api.status(PROC_UPGARDE)
    popen('apt upgrade -y > system_update.tmp')
    need_autoremove = False
    with open('system_update.tmp', 'r') as f:
        result = f.read()
        logger.info(result)
    if ('不需要' in result or 'no longer required' in result):
        logger.info('Found packages that can be autoremoved')
        need_autoremove = True
    os.remove('system_update.tmp')
    api.status(AUTH_AUTOREMOVE if need_autoremove else ALL_DONE)
    return need_autoremove


def aptAutoremove() -> None:
    logger.info('apt autoremove')
    api.status(PROC_AUTOREMOVE)
    popen('apt autoremove -y')
    api.status(ALL_DONE)


def getFiles(path:str = os.getcwd(), suffix:str = '') -> str:
    res = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(suffix):
                res.append(f)
    return res


def main() -> None:
    if(not aptUpdate()):
        api.status(UP_TO_DATE)
        logger.info('Up to date, exit...')
        return None
    if(not waitUntil(api.checkAuthorization, WAIT_HOLD, logger)):
        api.error('Not authorize with 24 hours')
        logger.critical('Not authorize with 24 hours, exit...')
        return None
    aptHold()
    if (not aptUpgrade()):
        logger.info('No need for autoremove, exit...')
        return None
    if(not waitUntil(api.checkAuthorization, WAIT_AUTOREMOVE, logger)):
        api.error('Not authorize with 24 hours')
        logger.critical('Not authorize with 24 hours, exit...')
        return None
    aptAutoremove()
    logger.info('All done! exit...')


if (__name__ == '__main__'):
    '''载入配置'''
    logging.info('Load config...')
    try:
        with open('system_update/conf.json', 'r') as f:
            conf = json.load(f)
    except FileNotFoundError as e:
        logging.critical(e)
        sys.exit()

    '''初始化logger'''
    logging.info('Init Logger...')
    logfile = os.path.join('system_update', '%s_%s.log' % (
        conf['client_name'],
        time.strftime('%Y%m%d', time.localtime(time.time()))
    ))
    logger = Logger(logfile=logfile, logdir='system_update')

    '''禁用urllib3警告'''
    logger.warning('urllib3 warnings disabled')
    urllib3.disable_warnings()

    '''检查环境'''
    logger.info('Check environment...')
    try:
        if (os.geteuid() != 0):
            logger.critical('This script must be run as root, exit...')
            sys.exit()
    except AttributeError:
        logger.critical('This script must be run in Linux, exit...')
        sys.exit()

    '''lock'''
    pid = checkLock()
    if (pid):
        logger.warning(f'Another upgrade process appears to be running, pid: {pid}')
        logger.warning('wait until lock is released...')
        if (not waitUntil(checkLock, 0, logger, max_retries=12)):
            logger.critical('Max retries exceeded, exit...')
            sys.exit()
    with open('system_update.lock', 'w') as f:
        f.write(str(os.getpid()))

    '''初始化Appwrite API'''
    logger.info('Init Appwrite API...')
    api = API(conf, logger)
    api.init()

    '''更新'''
    progs = []
    try:
        main()
    except Exception as e:
        logger.critical(e.__str__())

    '''上传log'''
    log_id = api.upload(logfile)['$id']
    try:
        api.post({f'log': '{api._endpoint}/storage/files/{log_id}/view?project={_project}'})
    except:
        pass

    '''清理log'''
    for logfile in getFiles('system_update', '.log'):
        created = time.mktime(time.strptime(logfile.replace(f'{conf["client_name"]}_', '').replace('.log', ''), '%Y%m%d'))
        if time.time() - created > 86400 * 7:
            os.unlink(os.path.join('system_update', logfile))

    '''lock'''
    os.unlink('system_update.lock')