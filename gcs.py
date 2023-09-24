from gcloud import storage
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
import os
import json
import base64
import binascii
from datetime import timedelta
import logging

## Logging ##
logger = logging.getLogger("appLog")
ConsoleOutputHandler = logging.StreamHandler()
logger.addHandler(ConsoleOutputHandler)
logger.setLevel("DEBUG")

LOCAL_DEV = True


class GCS:
    def __init__(self, project, bucket):
        self.project = project
        self.bucket = bucket
        if LOCAL_DEV:
            KEYFILE = '/Users/errol/gcpKeys/tstreck.json'
            if os.path.exists(KEYFILE):
                with open(KEYFILE) as jsonFile:
                    self.credentials_dict = json.load(jsonFile)
            else:
                logger.error("do something")
                exit(199)
            # print(credentials_dict)
            self.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                self.credentials_dict
            )
            # self.client = storage.Client(credentials=self.credentials,
            #  project=self.project)
        else:
            self.client = storage.Client()

    def uploadFile(self, file, filename, uploader, email):
        logger.info(f'Uploading: {filename}')
        client = storage.Client(credentials=self.credentials,
                                project=self.project)
        storageBucket = client.get_bucket(self.bucket)
        blob = storageBucket.blob(filename)
        blob.content_type = file.content_type

        try:

            blob.upload_from_file(file)
            # {'uploader': {uploader}, 'email': {email}}
            metadata = {'uploader': uploader, 'email': email}
            blob.metadata = metadata
            blob.patch()

        except Exception as e:

            logger.error(e)
            return False
        return True

    def generate_upload_signed_url_v4(self, blob_name):
        logger.debug('Generating Signed URL for {blob_name}')
        """Generates a v4 signed URL for uploading a blob using HTTP PUT.

        Note that this method requires a service account key file. You can not use
        this if you are using Application Default Credentials from Google Compute
        Engine or from the Google Cloud SDK.
        """
        # bucket_name = 'your-bucket-name'
        # blob_name = 'your-object-name'
        storage_client = storage.Client(credentials=self.credentials)
        bucket = storage_client.bucket(self.bucket)
        blob = bucket.blob(blob_name)

        url = blob.generate_signed_url(
            version="v4",
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
        logger.info(url)
        return url

    def fileExists(self, filename):
        logger.debug(f'Checking if {filename} exists')
        storage_client = storage.Client(credentials=self.credentials)
        bucket = storage_client.bucket(self.bucket)
        blob = bucket.blob(filename)
        logger.debug(f' Exists: {blob.exists()}')
        return blob.exists()

    def getFiles(self, prefix=None):
        logger.debug(f'Getting Files from {prefix}')
        storage_client = storage.Client(credentials=self.credentials)
        bucket = storage_client.bucket(self.bucket)

        return bucket.list_blobs(prefix=prefix)
        # for file in files:
        #     print("")
        # return files

    def listFiles(self, prefix=None):
        logger.debug(f'Listing Files from {prefix}')
        storage_client = storage.Client(credentials=self.credentials)
        bucket = storage_client.bucket(self.bucket)

        fileList = []
        for file in bucket.list_blobs(prefix=prefix):
            fileList.append(file.name)
        return fileList
        # for file in files:
        #     print("")
        # return files

    def dupExists(self, inputHash=None, prefix=None):
        logger.debug(f'Checking for Duplicates')
        storage_client = storage.Client(credentials=self.credentials)
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
        logger.debug(f'Getting Image {image}')
        blob = self.storageBucket.get_blob(image)
        logger.info(f'getImage: {blob} - {image}')
        content = blob.download_as_string()
        imageData = base64.b64encode(content).decode("utf-8")
        # print(blob.content_type)
        # print(type(content))
        # print(dir(imageData))
        return [imageData, blob.content_type, blob.metadata]


# gcs = GCS(project='theresastrecker', bucket='theresa-photo-storage')
# print(gcs.fileExists("uploads/dumpsterfire.jpg"))
# # print(fileExists("testFolder/dumpsterfsdfire.jpg"))
# print(gcs.listFiles())
if __name__ == "__main__":
    # Used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    gcs = GCS('theresastrecker', 'errol-test-bucket')
