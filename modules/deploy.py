import argparse
import logging
from common.constants import FUNCTIONS, LAYERS, FLASHBULB_BUCKET_PREFIX
from common.utils import get_function_by_key, get_function_name, get_function_s3_key, get_layer_name, get_layer_s3_key
import re
import boto3

logger = logging.getLogger('flashbulb.deploy')

def deploy_layer(key, region):
    aws_lambda = boto3.client('lambda', region_name=region)
    logger.info("Deploying {} layer in {}".format(key.title(), region))
    response = aws_lambda.publish_layer_version(
        LayerName=get_layer_name(key),
        Description=str(LAYERS[key]['version']),
        Content={
            'S3Bucket': FLASHBULB_BUCKET_PREFIX + region,
            'S3Key': get_layer_s3_key(key)
        },
        CompatibleRuntimes=LAYERS[key]['runtimes'],
    )
    return response


def deploy_function(key, region, role_arn):
    layer_arns = []
    for layer in FUNCTIONS[key]['layers']:
        layer_arns.append(deploy_layer(layer, region)['LayerVersionArn'])
    logger.info("Deploying {} function in {}".format(key.title(), region))
    aws_lambda = boto3.client('lambda', region_name=region)
    aws_lambda.create_function(
        FunctionName=get_function_name(key),
        Runtime=FUNCTIONS[key]['runtime'],
        Role=role_arn,
        Handler=FUNCTIONS[key]['handler'],
        Code={
            'S3Bucket': FLASHBULB_BUCKET_PREFIX + region,
            'S3Key': get_function_s3_key(key)
        },
        Description=str(FUNCTIONS[key]['version']),
        Timeout=FUNCTIONS[key]['timeout'],
        MemorySize=FUNCTIONS[key]['memory'],
        Publish=True,
        Layers=layer_arns
    )


def deploy_region(region, role_arn):
    for key, function in FUNCTIONS.items():
        result = get_function_by_key(key, region)
        if result is None:
            deploy_function(key, region, role_arn)


def deploy_regions(options):
    for region in options.regions:
        deploy_region(region, options.role_arn)
    logger.info('Done deploying Flashbulb across {} region{}'.format(len(options.regions), 's' if len(options.regions) > 1 else ''))
