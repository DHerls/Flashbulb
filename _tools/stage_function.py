from common.constants import FLASHBULB_DIR, FLASHBULB_BUCKET_PREFIX
from common.utils import check_function, get_function_s3_key
import pathlib
from zipfile import ZipFile
from _tools.global_upload import global_upload
import boto3
from botocore.exceptions import ClientError

def stage_function(key):
    aws_s3 = boto3.client('s3')
    try:
        aws_s3.head_object(Bucket=FLASHBULB_BUCKET_PREFIX + 'us-east-1', Key=get_function_s3_key(key))
        print("Did you forget to increment the {} function version?".format(key.title()))
        exit(-1)
    except ClientError:
        pass
    
    
    screenshot_dir = FLASHBULB_DIR.joinpath('lambdas').joinpath(key)
    zip_path = screenshot_dir.joinpath('function.zip')

    with ZipFile(zip_path, 'w') as myzip:
        myzip.write(screenshot_dir.joinpath('index.js'), arcname='index.js')

    global_upload(str(zip_path), get_function_s3_key(key))
