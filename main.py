import hashlib
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import gcs


app = Flask(__name__)

## Globals ##
app.config['MAX_CONTENT_LENGTH'] = 784 * 1024 * 1024  # 784 MB
app.config['UPLOAD_FOLDER'] = "uploads/"
app.config['GCS_UPLOAD'] = True
cloudStorage = gcs.GCS(project='theresastrecker',
                       bucket='theresa-photo-storage')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif', 'webp', 'tif',
                      'tiff', 'raw', 'bmp', 'pdf', 'mpeg', 'mpg', 'ogg', 'mp4', 'avi', 'mov'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def upload():
    return render_template('tsCOL/index.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('tsCOL/index.html'), 404


@app.route('/', methods=['POST'])
def upload_file():
    files = request.files.getlist('file')
    formInfo = request.values
    print(files)
    uploadCount = len(request.files.getlist('file'))
    for file in files:
        print(file.filename)
        if file.filename and allowed_file(file.filename):
            longFileName = prepareFileName(secure_filename(file.filename))
            filename = longFileName.split(app.config['UPLOAD_FOLDER'], 1)[1]
            if app.config['GCS_UPLOAD']:
                fileHash = hashlib.md5(file.read()).hexdigest()
                file.seek(0)
                if not cloudStorage.dupExists(fileHash) and not cloudStorage.fileExists(filename):
                    print("Uploading File")
                    cloudStorage.uploadFile(
                        file, f"{app.config['UPLOAD_FOLDER']}{filename}", formInfo['name'], formInfo['email'])
                else:
                    print("Image has already been uploaded")
                # return 'File Successfully Uploaded to GCS'
        elif not file.filename:
            return 'No file in the request', 400
        elif file and not allowed_file(file.filename):
            return 'This File type is not allowed', 400

    return render_template('tsCOL/thanks.html', fileCount=uploadCount)


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    return 'File is too large', 413


def prepareFileName(fileExists, iter=1):
    if not app.config['UPLOAD_FOLDER'] in fileExists:
        fileExists = os.path.join(app.config['UPLOAD_FOLDER'], fileExists)
    if app.config['GCS_UPLOAD']:
        if not cloudStorage.fileExists(fileExists):
            return fileExists.lower()

    baseFile = f'{fileExists.rsplit(".", 1)[0].lower()}'
    fileExt = f'.{fileExists.rsplit(".", 1)[1].lower()}'
    if f'-{iter}' in baseFile:
        baseFile = f'{baseFile.rsplit("-", 1)[0]}'
        iter = iter + 1
    fileExists = f'{baseFile}-{iter}{fileExt}'
    return prepareFileName(fileExists, iter)


@app.route("/images/<string:blob_name>")
def view(blob_name):
    values = cloudStorage.getImage(f'uploads/{blob_name}')
    return render_template('tsCol/images.html', content_type=values[1],  image=values[0], imageName=blob_name, metadata=values[2])


if __name__ == "__main__":
    # Used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    app.run(host="localhost", port=8080, debug=True)
