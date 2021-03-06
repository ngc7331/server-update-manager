'''V1.2'''
import os
import time
import logging

loggers = {}
class Logger(logging.Logger):
    def __init__(self, name:str = 'root', init_filehandler:bool = True, logfile:str = None, logdir:str = 'log'):
        super().__init__(name, logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")

        self._consolehandler = logging.StreamHandler()
        self._consolehandler.setLevel(logging.DEBUG)
        self._consolehandler.setFormatter(formatter)
        self.addHandler(self._consolehandler)

        if (init_filehandler):
            if (not os.path.exists(logdir)):
                os.mkdir(logdir)
            if (logfile is None):
                logfile = os.path.join(logdir, '%s.log' % time.strftime('%Y%m%d%H%M', time.localtime(time.time())))
            self._filehandler = logging.FileHandler(logfile, 'w', encoding='gbk')
            self._filehandler.setLevel(logging.INFO)
            self._filehandler.setFormatter(formatter)
            self.addHandler(self._filehandler)

        loggers.update({name: self})

    def SetLevel(self, level:int, handler:str = 'console') -> None:
        handler = handler.lower()
        if (handler == 'file'):
            self._filehandler.setLevel(level)
        else:
            self._consolehandler.setLevel(level)

def getLogger(name:str = 'root'):
    if (len(loggers.keys()) == 0):
        return Logger(name)
    if not name in loggers.keys():
        return None
    else:
        return loggers[name]