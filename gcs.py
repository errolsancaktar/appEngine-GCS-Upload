from gcloud import storage
from google.cloud import secretmanager
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import base64
import binascii
from datetime import timedelta
import logging
import google.cloud.logging_v2
from google.cloud.logging_v2.handlers import CloudLoggingHandler
import sys


## Variables
LOCAL_DEV = False

## Class Definition
class GCS:
    def __init__(self, project, bucket):
        self.project = project
        self.bucket = bucket

        ## Set up Secret Manager for Elevated Access ##
        secretClient = secretmanager.SecretManagerServiceClient()
        response = self.getSecret()
        self.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(response)
        )

        logging.info("Setup Logging")
        if not LOCAL_DEV:
            self.logger = self.setupCloudLogging()
            self.logger.setLevel("DEBUG")
        else:
            self.logger = logging.getLogger()
            self.logger.setLevel("DEBUG")

    def setupCloudLogging(self):
        logging_client = google.cloud.logging_v2.Client()
        handler = CloudLoggingHandler(logging_client)
        # Set Cloud Side
        self.logger = logging.getLogger('cloudLogger')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)

        self.logger.info("Cloud Logging Setup")
        return self.logger

    def getSecret(self):
        secretClient = secretmanager.SecretManagerServiceClient()
        response = secretClient.access_secret_version(
            name='projects/422051208073/secrets/tstrec_sa/versions/latest')
        return response.payload.data.decode('UTF-8')

    def getClient(self):

        storage_client = storage.Client(
            credentials=self.credentials, project=self.project)
        return storage_client

    def uploadFile(self, file, filename, uploader, email):
        self.logger.info(f'Uploading: {filename}')
        client = self.getClient()
        storageBucket = client.get_bucket(self.bucket)
        blob = storageBucket.blob(filename)
        blob.content_type = file.content_type

        try:
            blob.upload_from_file(file)

        except Exception as e:

            self.logger.error(e)
            return False
        return True

    def addMetadata(self, filename, uploader, email):

        # Client Creds #
        storage_client = self.getClient()
        bucket = storage_client.bucket(self.bucket)

        # Pull Blob by Filename #
        blob = bucket.blob(filename)

        # Create metadata object and patch
        metadata = {'uploader': uploader, 'email': email}
        blob.metadata = metadata
        blob.patch()

        # Verify

        blob = bucket.blob(filename)
        self.logger.debug(
            f"Patched Metadata, New Data is: name: {uploader} - email: {email}")

    def generate_upload_signed_url_v4(self, blob_name):
        self.logger.debug('Generating Signed URL for {blob_name}')
        """Generates a v4 signed URL for uploading a blob using HTTP PUT.

        Note that this method requires a service account key file. You can not use
        this if you are using Application Default Credentials from Google Compute
        Engine or from the Google Cloud SDK.
        """
        # bucket_name = 'your-bucket-name'
        # blob_name = 'your-object-name'
        storage_client = self.getClient()
        bucket = storage_client.bucket(self.bucket)
        blob = bucket.blob(blob_name)

        url = blob.generate_signed_url(
            # version="v4",
            # This URL is valid for 15 minutes
            expiration=timedelta(minutes=15),
            # Allow PUT requests using this URL.
            method="PUT",
            content_type="application/octet-stream",
        )

        # print("Generated PUT signed URL:")
        # print(url)
        # print("You can use this URL with any user agent, for example:")
        # print(
        #     "curl -X PUT -H 'Content-Type: application/octet-stream' "
        #     "--upload-file my-file '{}'".format(url)
        # )
        self.logger.info(url)
        return url

    def fileExists(self, filename):
        self.logger.debug(f'Checking if {filename} exists')
        storage_client = self.getClient()
        bucket = storage_client.bucket(self.bucket)
        blob = bucket.blob(filename)
        self.logger.debug(f' Exists: {blob.exists()}')
        return blob.exists()

    def getFiles(self, prefix=None):
        self.logger.debug(f'Getting Files from {prefix}')
        storage_client = self.getClient()
        bucket = storage_client.bucket(self.bucket)

        return bucket.list_blobs(prefix=prefix)
        # for file in files:
        #     print("")
        # return files

    def listFiles(self, prefix=None):
        self.logger.debug(f'Listing Files from {prefix}')
        storage_client = self.getClient()
        bucket = storage_client.bucket(self.bucket)

        fileList = []
        for file in bucket.list_blobs(prefix=prefix):
            fileList.append(file.name)
        fileList.sort(reverse=True)
        self.logger.debug(f'Filelist: {fileList}')
        return fileList
        # for file in files:
        #     print("")
        # return files

    def dupExists(self, inputHash=None, prefix=None):
        self.logger.debug(f'Checking for Duplicates')
        storage_client = self.getClient()
        bucket = storage_client.bucket(self.bucket)

        for i in self.listFiles(prefix):
            blob = bucket.get_blob(i)
            hash = binascii.hexlify(base64.urlsafe_b64decode(blob.md5_hash))
            fileHash = bytes.decode(hash, 'utf-8')
            # print(f'Inp: {inputHash}\nCur: {fileHash}')
            if inputHash == fileHash:
                return True
        return False

    def getImage(self, image):
        storage_client = self.getClient()
        bucket = storage_client.bucket(self.bucket)
        self.logger.debug(f'Getting Image {image}')
        blob = bucket.get_blob(image)
        self.logger.info(f'getImage: {blob} - {image}')
        content = blob.download_as_string()
        imageData = base64.b64encode(content).decode("utf-8")
        # print(blob.content_type)
        # print(type(content))
        # print(dir(imageData))
        return [imageData, blob.content_type, blob.metadata]

    def hashDecode(self, hash):
        hashByte = binascii.hexlify(base64.urlsafe_b64decode(hash))
        return bytes.decode(hashByte, 'utf-8')

    def getHash(self, file):
        storage_client = self.getClient()
        bucket = storage_client.bucket(self.bucket)
        blob = bucket.get_blob(file)
        hash = self.hashDecode(blob.md5_hash)
        return hash

    def cleanDupes(self, prefix=None):
        dupeCount = 0
        self.logger.info(f'Cleaning Duplicates')
        storage_client = self.getClient()
        bucket = storage_client.bucket(self.bucket)

        ## Generate Hashes from all Files in Prefix ##
        files = self.listFiles(prefix)
        hashes = []
        for file in files:
            hashes.append({'name': file, 'hash': self.getHash(file)})
        print(hashes)
        for i in hashes:
            self.logger.debug(f"Looking at: {i['name']}")
            curHash = i['hash']
            # for j in self.listFiles(prefix):
            for j in hashes:
                try:
                    if curHash == j['hash'] and i['name'] != j['name']:
                        self.logger.info(
                            f"Duplicate of {i['name']} - {i['hash']} found at: {j['name']} - {j['hash']}")
                        blob = bucket.get_blob(j['name'])
                        blob.delete()
                        self.logger.debug(f"{i['name']} - {j['name']}")
                        for element in range(len(hashes)):
                            if hashes[element]['name'] == j['name']:
                                logging.debug(f"Removing Element: {j['name']}")
                                del hashes[element]
                                break
                        dupeCount += 1
                        self.logger.info(f'Deleting: {blob.name}')
                except AttributeError as e:
                    self.logger.info(f"Finished Files - {e}")
        self.logger.info(f'Completed - removed {dupeCount}')
        return dupeCount


# gcs = GCS(project='theresastrecker', bucket='theresa-photo-storage')
# print(gcs.fileExists("uploads/dumpsterfire.jpg"))
# # print(fileExists("testFolder/dumpsterfsdfire.jpg"))
# print(gcs.listFiles())
if __name__ == "__main__":
    LOCAL_DEV = False
    # Used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    gcs = GCS('theresastrecker', 'errol-test-bucket')
    # gcs.cleanDupes("test/")
    # gcs.generate_upload_signed_url_v4("test")
