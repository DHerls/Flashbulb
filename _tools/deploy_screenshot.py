
from zipfile import ZipFile
import pathlib

from _tools.global_upload import global_upload
from common.constants import SCREENSHOT_S3_KEY
from common.utils import check_screenshot_lambda

def deploy_screenshot():
    if check_screenshot_lambda('us-east-1'):
        print("Did you forget to increment the lambda function version?")
        exit(-1)
        

    flashbulb_dir = pathlib.Path(__file__).parent.parent.absolute()
    screenshot_dir = flashbulb_dir.joinpath('lambdas').joinpath('screenshot')
    zip_path = screenshot_dir.joinpath('function.zip')

    with ZipFile(zip_path, 'w') as myzip:
        myzip.write(screenshot_dir.joinpath('index.js'), arcname='index.js')

    global_upload(str(zip_path), SCREENSHOT_S3_KEY)
