'''
version 2022.05.16.1 dev
'''
from re import A
from appwrite.client import Client
from appwrite.services.database import Database
from appwrite.services.storage import Storage
from modules.color import Green
from modules.const import *
from modules.Logger import Logger, getLogger
import os
import time


class API():
    def __init__(self, conf:dict, logger:Logger=getLogger()) -> None:
        # Load conf
        self.name = conf['client_name']
        self._bucket = conf['bucket']
        self._collection_id = conf['collection']
        self._endpoint = conf['endpoint']
        self._key = conf['key']
        self._project = conf['project']
        self._permission = conf['permission']
        self._logger = logger
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
        if self.name in clients.keys():
            self._document_id = clients[self.name]
            self._logger.info(f'Get document id: {Green(self._document_id)}')
        else:
            self._document_id = None

    def post(self, **data):
        '''Post data to collection by update or create a document'''
        if 'time' not in data:
            data.update(time = time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(time.time())))
        if self._document_id is not None:
            return self._database.update_document(
                self._collection_id, self._document_id, data,
                self._permission, self._permission
            )
        else:
            data.update(name = self.name)
            result = self._database.create_document(
                self._collection_id, 'unique()', data,
                self._permission, self._permission
            )
            self._document_id = result['$id']
            return result
    def remove(self):
        '''Remove document from collection'''
        if self._document_id is None:
            return None
        result = self._database.delete_document(
            self._collection_id, self._document_id
        )
        self._document_id = None
        return result

    def init(self) -> None:
        self.post(
            error = False,
            status = INIT,
            msg = ''
        )

    def status(self, status:int) -> None:
        self._logger.info(f'status {self._status} -> {status} post to api')
        self._status = status
        self.post(status = status)

    def error(self, msg:str) -> None:
        self.post(error = True, msg = msg)
    def fatal(self, msg:str) -> None:
        self.post(status = FATAL, error = True, msg = msg)

    def checkAuthorization(self) -> int:
        document = self._database.get_document(self._collection_id, self._document_id)
        return document['status']

    def upload(self, filepath:str):
        if not os.path.exists(filepath):
            return None
        return self._storage.create_file(
            self._bucket, 'unique()', filepath,
            self._permission, self._permission
        )
