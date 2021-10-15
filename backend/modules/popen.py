# version 1.1
from subprocess import Popen,PIPE,DEVNULL
from sys import stdout
import logging
def popen(cmd, output = False, output_filter = []):
    def ListInStr(l, s):
        ans = True
        for obj in l:
            if(obj not in s):
                ans = False
        return ans
    logging.debug("Executing '\033[34m%s\033[0m'" % cmd)
    p = Popen(
        cmd,
        shell = True,
        stdout=PIPE,
        stderr=PIPE,
        stdin=DEVNULL
    )
    if (output):
        maxlen = 0
        while p.poll() is None:
            if (output_filter):
                lines = p.stdout.readline().decode().split('\n')
                for line in lines:
                    if (ListInStr(output_filter, line)):
                        msg = line[line.find(output_filter[0]):]
                        if (len(msg) > maxlen):
                            maxlen = len(msg)
                        stdout.write('\r' + msg + ' '*(maxlen-len(msg)))
                        stdout.flush()
            else:
                stdout.write(p.stdout.readline().decode())
        print()
    else:
        p.wait()
    if (p.poll()):
        return p.stderr
    return p.stdout