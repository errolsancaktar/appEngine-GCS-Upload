from gcloud import storage
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import base64
import hashlib

DEBUG = True
KEYFILE = os.environ['SA_KEY']


class GCS:
    def __init__(self, project, bucket):
        self.project = project
        self.bucket = bucket
        if "BACKUP_CLIENT_ID" in os.environ:
            self.credentials_dict = {
                'type': 'service_account',
                'client_id': os.environ['BACKUP_CLIENT_ID'],
                'client_email': os.environ['BACKUP_CLIENT_EMAIL'],
                'private_key_id': os.environ['BACKUP_PRIVATE_KEY_ID'],
                'private_key': os.environ['BACKUP_PRIVATE_KEY'],
            }
        elif os.path.exists(KEYFILE):
            with open(KEYFILE) as jsonFile:
                self.credentials_dict = json.load(jsonFile)
        else:
            print("do something")
            exit(199)
        # print(credentials_dict)
        self.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            self.credentials_dict
        )
        self.client = storage.Client(credentials=self.credentials,
                                     project=self.project)
        self.bucket = self.client.get_bucket(self.bucket)

    def uploadFile(self, file, filename):
        if DEBUG:
            print(f'Starting Upload of: {filename}')
        blob = self.bucket.blob(filename)
        blob.content_type = file.content_type
        if DEBUG:
            print(blob)
        try:
            if DEBUG:
                print(file)
            # blob.upload_from_filename(file)
            blob.upload_from_file(file)
            # print(blob.content_type)
        except Exception as e:
            print(e)
            print("Upload Failed")

    def fileExists(self, filename):
        # print(filename)
        files = self.bucket.list_blobs()
        for file in files:
            if filename in file.name:
                return True
        else:
            # print("False")
            return False

    def listFiles(self, prefix=None):
        return self.bucket.list_blobs(prefix=prefix)
        # for file in files:
        #     print("")
        # return files

    def getFileList(self, prefix=None):
        # files = storageBucket.list_blobs(prefix='uploads/')
        fileList = []
        files = self.listFiles(prefix=prefix)
        for file in files:
            fileList.append(file.name)
        return fileList

    def dupExists(self, inputHash=None, prefix='uploads'):
        print("Comparing Hashes")
        print(self.getFileList(prefix))
        for i in self.getFileList(prefix):
            print(inputHash)
            curHas = hashlib.md5(self.bucket.get_blob(
                i).download_as_string()).hexdigest()
            print(curHas)
            if inputHash == curHas:
                return True
        return False

    def getImage(self, image):
        blob = self.bucket.get_blob(f'uploads/{image}')
        content = image.download_as_bytes()
        imageData = base64.b64encode(content).decode("utf-8")
        print(image)
        return [image.content_type, imageData]
# gcs = GCS(project='theresastrecker', bucket='theresa-photo-storage')
# print(gcs.fileExists("uploads/dumpsterfire.jpg"))
# # print(fileExists("testFolder/dumpsterfsdfire.jpg"))
# print(gcs.listFiles())
