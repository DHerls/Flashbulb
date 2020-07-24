
import boto3
from common.constants import FLASHBULB_DIR
from pathlib import Path
import os
import glob
import json
import io
import pathlib
import logging

logger = logging.getLogger('flashbulb.report')

def combine_json(bucket, prefix):
    logger.info("Analyzing reports")
    aws_s3 = boto3.client('s3')
    paginator = aws_s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(
        Bucket=bucket,
        Prefix=prefix
    )

    data = []
    buffer = b'{"targets":['

    for page in page_iterator:
        for obj in page['Contents']:
            if obj['Key'].endswith('.json'):
                temp_buffer = io.BytesIO(b'')
                aws_s3.download_fileobj(bucket, obj['Key'], temp_buffer)
                temp_buffer.seek(0)
                buffer += temp_buffer.getvalue()
                buffer += b','
    # Trailing commas aren't allowed by JSON spec
    buffer = buffer[:-1]
    buffer += b"]}"
    temp_buffer = io.BytesIO(buffer)
    aws_s3.upload_fileobj(temp_buffer, bucket, prefix + 'combined.json')  


def upload_index(bucket, prefix):
    index_file = FLASHBULB_DIR.joinpath('assets').joinpath('index.html')
    aws_s3 = boto3.client('s3')
    with open(index_file, encoding='utf-8') as f:
        aws_s3.put_object(Bucket=bucket, Key=prefix + 'index.html', Body=f.read(), ContentType='text/html')
    logger.info(f'Visit https://{bucket}.s3.amazonaws.com/{prefix}index.html to see the report.')


def run_report(bucket, prefix):
    combine_json(bucket, prefix)
    upload_index(bucket, prefix)
