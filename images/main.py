import hashlib
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import gcs


app = Flask(__name__)

## Globals ##
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024  # 256 MB
app.config['UPLOAD_FOLDER'] = "uploads/"
app.config['GCS_UPLOAD'] = True
app.config['LOCAL_UPLOAD'] = False
DEBUG = True
cloudStorage = gcs.GCS(project='theresastrecker',
                       bucket='theresa-photo-storage')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif', 'webp', 'tif',
                      'tiff', 'raw', 'bmp', 'pdf', 'mpeg', 'mpg', 'ogg', 'mp4', 'avi', 'mov'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def upload():
    return render_template('upload.html')


@app.route('/', methods=['POST'])
def upload_file():
    files = request.files.getlist('file')
    if 'file' not in request.files:
        print("problem")
    print(files)
    for file in files:
        # if 'file' in request.files:
        # file = request.files['file']
        # print(dir(request.files))
        # print(request.files)
        if file and allowed_file(file.filename):
            longFileName = prepareFileName(secure_filename(file.filename))
            filename = longFileName.split(app.config['UPLOAD_FOLDER'], 1)[1]
            if app.config['LOCAL_UPLOAD']:
                if DEBUG:
                    print(
                        f'Trying to save file: {secure_filename(file.filename)} as: {longFileName}, {type(longFileName)}')
                file.save(longFileName)
                if DEBUG:
                    print('File uploaded successfully')
            if app.config['GCS_UPLOAD']:
                if DEBUG:
                    print(f'GCS: {filename}')
                fileHash = hashlib.md5(file.read()).hexdigest()
                file.seek(0)
                if not cloudStorage.dupExists(fileHash) and not cloudStorage.fileExists(filename):
                    print("Uploading File")
                    cloudStorage.uploadFile(
                        file, f"{app.config['UPLOAD_FOLDER']}{filename}")
                else:
                    print("Image has already been uploaded")
                # return 'File Successfully Uploaded to GCS'
        elif 'file' not in file.name:
            return 'No file in the request', 400
        elif file and not allowed_file(file.filename):
            return 'This File type is not allowed', 400

    return 'Thank you for sharing!'


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    return 'File is too large', 413


def prepareFileName(fileExists, iter=1):
    if not app.config['UPLOAD_FOLDER'] in fileExists:
        fileExists = os.path.join(app.config['UPLOAD_FOLDER'], fileExists)
    if DEBUG:
        print("Starting File Check")
    if app.config['LOCAL_UPLOAD']:
        if DEBUG:
            print(os.path.isfile(fileExists))
        if not os.path.isfile(fileExists):
            if DEBUG:
                print(f'return:{fileExists}')
            return fileExists.lower()
    if app.config['GCS_UPLOAD']:
        if DEBUG:
            print(cloudStorage.fileExists(fileExists))
        if not cloudStorage.fileExists(fileExists):
            if DEBUG:
                print(f'GCS FileName:{fileExists}')
            return fileExists.lower()

    if DEBUG:
        print('File exists')
    baseFile = f'{fileExists.rsplit(".", 1)[0].lower()}'
    fileExt = f'.{fileExists.rsplit(".", 1)[1].lower()}'
    if DEBUG:
        print(baseFile)
    if DEBUG:
        print(f'-{iter}')
    if f'-{iter}' in baseFile:
        if DEBUG:
            print("iter found")
        baseFile = f'{baseFile.rsplit("-", 1)[0]}'
        iter = iter + 1
        if DEBUG:
            print(f'Base File Name: {baseFile}')
    fileExists = f'{baseFile}-{iter}{fileExt}'
    if DEBUG:
        print(f'New Filename: {fileExists}')
    return prepareFileName(fileExists, iter)


@app.route("/images/<string:blob_name>")
def view(blob_name):
    values = cloudStorage.getImage(blob_name)
    return render_template('images.html', content_type=values[0],  image=values[1])


if __name__ == '__main__':
    app.run(debug=True)
