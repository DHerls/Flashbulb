import logging
import argparse

from common.constants import  FLASHBULB_BUCKET_PREFIX, FUNCTIONS, LAYERS
from common.utils import SemanticVersion,check_function, check_layer, get_function_name, get_function_s3_key, get_layer_name, get_layer_s3_key
import boto3


logger = logging.getLogger('flashbulb.update')


def update_layer(key, region):
    logger.info("Updating {} layer in {}".format(key.title(), region))
    aws_lambda = boto3.client('lambda', region_name=region)
    response = aws_lambda.publish_layer_version(
        LayerName=get_layer_name(key),
        Description=str(LAYERS[key]['version']),
        Content={
            'S3Bucket': FLASHBULB_BUCKET_PREFIX + region,
            'S3Key': get_layer_s3_key(key)
        },
        CompatibleRuntimes=LAYERS[key]['runtimes'],
    )
    for func_key, function in FUNCTIONS.items():
        if key in function['layers']:
            aws_lambda.update_function_configuration(
                FunctionName=get_function_name(func_key),
                Layers=[
                    response['LayerVersionArn']
                ]
            )


def update_function(key, region):
    logger.info("Updating {} function in {}".format(key.title(), region))
    aws_lambda = boto3.client('lambda', region_name=region)
    aws_lambda.update_function_code(
        FunctionName=get_function_name(key),
        S3Bucket=FLASHBULB_BUCKET_PREFIX + region,
        S3Key=get_function_s3_key(key)
    )
    aws_lambda.update_function_configuration(
        FunctionName=get_function_name(key),
        Description=str(FUNCTIONS[key]['version'])
    )


def update_region(region):
    for key in LAYERS.keys():
        if not check_layer(key, region):
            update_layer(key, region)
    
    for key in FUNCTIONS.keys():
        if not check_function(key, region):
            update_function(key, region)
    

def update_regions(options):
    for region in options.regions:
        update_region(region)
    logger.info("Update complete")

