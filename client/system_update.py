from appwrite.client import Client
from appwrite.services.database import Database
from appwrite.services.storage import Storage
import json
import logging
from modules.popen import popen
from modules.Logger import Logger
import os
import sys
import time
from urllib3 import disable_warnings

def Green(msg:str) -> str:
    return '\033[32m%s\033[0m' % msg

class API():
    def __init__(self, conf:dict, logger:Logger=None) -> None:
        # Load conf
        self.name = conf['client_name']
        self._collection_id = conf['collection']
        self._permission = conf['permission']
        self._logger = logger if logger is not None else Logger()

        # Init Client, Database and Storage
        self._client = Client()
        self._client.set_endpoint(conf['endpoint'])\
            .set_project(conf['project'])\
            .set_key(conf['key'])
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

    def Post(self, data:dict):
        '''Post data to collection by update or create a document'''
        if (self._document_id is not None):
            return self._database.update_document(
                self._collection_id, self._document_id, data,
                self._permission, self._permission
            )
        else:
            result = self._database.create_document(
                self._collection_id, 'unique()', data,
                self._permission, self._permission
            )
            self._document_id = result['$id']
            return result
    def Remove(self):
        '''Remove document from collection'''
        if (self._document_id is None):
            return None
        result = self._database.delete_document(
            self._collection_id, self._document_id
        )
        self._document_id = None
        return result

    def checkAuthorization(self, name:str = 'authorized') -> bool:
        document = self._database.get_document(self._collection_id, self._document_id)
        return document[name]

    def waitUntilAuthorized(self, name:str = 'authorized', interval:float = 300, retries:int = 0, max_retries:int = 288) -> bool:
        if (retries > max_retries):
            return False
        if (not self.checkAuthorization(name)):
            self._logger.debug('not authorized, sleep %f seconds' % interval)
            time.sleep(interval)
            return self.waitUntilAuthorized(name, interval, retries+1, max_retries)
        return True

    def Upload(self, filepath:str):
        if (not os.path.exists(filepath)):
            return None
        return self._storage.create_file(
            'unique()', open(filepath, 'rb'),
            self._permission, self._permission
        )

def AptUpdate() -> bool:
    logger.info('apt update')
    popen('apt update > system_update.tmp')
    with open('system_update.tmp', 'r') as f:
        result = f.read()
        logger.debug(result)
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
    result = api.Post({
        'name': api.name,
        'progs': progs,
        'authorized': False,
        'success': False,
        'autoremove': False,
        'need_autoremove': False,
        'all_done': False
    })
    document_id = result['$id']
    logger.debug(result)
    logger.info('Status posted to api, document id: %s' % Green(document_id))
    return True

def AptHold() -> None:
    logger.info('set apt hold')
    hold_list = popen('apt-mark showhold').read().decode()
    for prog in progs:
        prog = json.loads(prog)
        if (prog['name'] in hold_list and not prog['hold']):
            logger.info('Unhold %s, it will be upgraded from %s to %s' % (
                prog['name'], prog['version'][1], prog['version'][0]))
            popen('apt-mark unhold %s' % prog['name'])
        elif (prog['name'] not in hold_list and prog['hold']):
            logger.info('Hold %s at version %s' % (prog['name'], prog['version'][1]))
            popen('apt-mark hold %s' % prog['name'])
    return None

def AptUpgrade() -> bool:
    logger.info('apt upgrade')
    popen('apt upgrade -y > system_update.tmp')
    need_autoremove = False
    with open('system_update.tmp', 'r') as f:
        result = f.read()
        logger.debug(result)
    if ('不需要' in result or 'no longer required' in result):
        logger.info('Found packages that can be autoremoved')
        need_autoremove = True
    os.remove('system_update.tmp')
    logger.info('Post API')
    api.Post({
        'success': True,
        'need_autoremove': need_autoremove,
        'all_done': not need_autoremove
    })
    return need_autoremove

def AptAutoremove() -> None:
    logger.info('apt autoremove')
    popen('apt autoremove -y')
    logger.info('Post API')
    api.Post({
        'all_done': True
    })
    return None

def exit() -> None:
    api.Upload(logfile)
    sys.exit()

if (__name__ == '__main__'):
    '''禁用urllib3警告'''
    disable_warnings()

    '''检查环境'''
    logging.info('Check environment...')
    try:
        if (os.geteuid() != 0):
            logging.critical('This script must be run as root, exit...')
            sys.exit()
    except AttributeError:
        logging.critical('This script must be run in Linux, exit...')
        sys.exit()

    '''载入配置'''
    try:
        with open('system_update/conf.json', 'r') as f:
            conf = json.load(f)
    except FileNotFoundError as e:
        logging.critical(e)
        sys.exit()

    '''初始化API & logger'''
    logging.info('Init Logger & API...')
    logfile = os.path.join('system_update', '%s_%s.log' % (
        conf['client_name'],
        time.strftime('%Y%m%d', time.localtime(time.time()))
    ))
    logger = Logger(logfile=logfile, logdir='system_update')
    api = API(conf, logger)

    '''更新'''
    up_to_date = False
    progs = []
    if(not AptUpdate()):
        logger.info('Up to date, exit...')
        exit()
    if(not api.waitUntilAuthorized()):
        logger.critical('Not authorize with 24 hours, exit...')
        exit()
    AptHold()
    if (not AptUpgrade()):
        logger.info('No need for autoremove, exit...')
        exit()
    if(not api.waitUntilAuthorized('autoremove')):
        logger.critical('Not authorize with 24 hours, exit...')
        exit()
    AptAutoremove()
    logger.info('All done! exit...')
    exit()