'''
version 2022.05.16.1 dev
'''
def Green(msg:str) -> str:
    return f'\033[32m{msg}\033[0m'

def Yellow(msg:str) -> str:
    return f'\033[33m{msg}\033[0m'

def Red(msg:str) -> str:
    return f'\033[31m{msg}\033[0m'