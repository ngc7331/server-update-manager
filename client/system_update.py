'''
version 2022.05.16.1 dev
'''
import json
import logging
from modules.API import API
from modules.const import *
from modules.color import Green
from modules.Logger import Logger, getLogger
from modules.popen import popen
import os
import psutil
import sys
import time
import urllib3


def keyboardInterruptHandler() -> None:
    logger.info('Keyboard interrupt: ')
    input('To exit, press ctrl+c again; else, press enter.')


def waitUntil(check, target_status:int, logger:Logger = getLogger(),
              interval:float = 300, retries:int = 0, max_retries:int = 288) -> bool:
    if retries > max_retries:
        return False
    status = check()
    if status != target_status:
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
    if not psutil.Process(pid).name() in ['python3', 'python']:
        return 0
    return pid


def parseErr(msg: str) -> str:
    res = []
    for line in msg.splitlines():
        if (line.startswith('E:') or
            line.startswith('Err:') or
            line.startswith('W:') or
            line.startswith('Warn:') or
            line.startswith('error') or
            line.startswith('warning')
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
    if err:
        api.error(f'apt update completed with error:\n{err}')
        logger.error('apt update completed with error, trying to ignore')
        logger.warning(err)
    if 'apt list --upgradable' not in result:
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
        if '正在列表' in line or 'Listing' in line:
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
        if prog in hold_list:
            line = '[Hold] ' + line
        msg += line
    logger.info(msg)
    logger.info('Post API')
    result = api.post(
        progs = progs,
        status = AUTH_UPGRADE
    )
    document_id = result['$id']
    logger.debug(result)
    logger.info(f'Status posted to api, document id: {Green(document_id)}')
    return True


def aptHold() -> None:
    logger.info('set apt hold')
    api.status(PROC_HOLD)
    hold_list = popen('apt-mark showhold').read().decode()
    for prog in progs:
        prog = json.loads(prog)
        if prog['name'] in hold_list and not prog['hold']:
            logger.info('Unhold {name}, it will be upgraded from {version[1]} to {versiob[0]}'.format(**prog))
            popen(f'apt-mark unhold {prog["name"]}')
        elif prog['name'] not in hold_list and prog['hold']:
            logger.info('Hold {name} at version {version[1]}'.format(**prog))
            popen(f'apt-mark hold {prog["name"]}')
    api.status(WAIT_UPGRADE)


def aptUpgrade() -> bool:
    logger.info('apt upgrade')
    api.status(PROC_UPGARDE)
    popen('apt upgrade -y > system_update.tmp')
    need_autoremove = False
    with open('system_update.tmp', 'r') as f:
        result = f.read()
        logger.info(result)
    if '不需要' in result or 'no longer required' in result:
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
    if not aptUpdate():
        api.status(UP_TO_DATE)
        logger.info('Up to date, exit...')
        return None
    if not waitUntil(api.checkAuthorization, WAIT_HOLD, logger):
        api.error('Not authorize with 24 hours')
        logger.critical('Not authorize with 24 hours, exit...')
        return None
    aptHold()
    if not aptUpgrade():
        logger.info('No need for autoremove, exit...')
        return None
    if not waitUntil(api.checkAuthorization, WAIT_AUTOREMOVE, logger):
        api.error('Not authorize with 24 hours')
        logger.critical('Not authorize with 24 hours, exit...')
        return None
    aptAutoremove()
    logger.info('All done! exit...')


if __name__ == '__main__':
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
    logfile = os.path.join('system_update', '{}_{}.log'.format(
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
        if os.geteuid() != 0:
            logger.critical('This script must be run as root, exit...')
            sys.exit()
    except AttributeError:
        logger.critical('This script must be run in Linux, exit...')
        sys.exit()

    '''lock'''
    pid = checkLock()
    if pid:
        logger.warning(f'Another upgrade process appears to be running, pid: {pid}')
        logger.warning('wait until lock is released...')
        if not waitUntil(checkLock, 0, logger, max_retries=12):
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
        api.post(log = f'{api._endpoint}/storage/files/{log_id}/view?project={api._project}&mode=admin')
    except:
        pass

    '''清理log'''
    for logfile in getFiles('system_update', '.log'):
        created = time.mktime(time.strptime(logfile.replace(f'{conf["client_name"]}_', '').replace('.log', ''), '%Y%m%d'))
        if time.time() - created > 86400 * 7:
            os.unlink(os.path.join('system_update', logfile))

    '''lock'''
    os.unlink('system_update.lock')