import argparse
import logging
from common.constants import FUNCTIONS, LAYERS, FLASHBULB_BUCKET_PREFIX
from common.utils import check_credentials, get_function_by_key, get_function_name, get_function_s3_key, get_layer_name, get_layer_s3_key, parse_regions
import re
import boto3


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


def deploy(regions, role_arn):
    for region in regions:
        deploy_region(region, role_arn)
    logger.info('Done deploying Flashbulb across {} region{}'.format(len(regions), 's' if len(regions) > 1 else ''))


def parse_lambda_execution_role(user_input):
    if not re.match(r'arn:aws:iam::[0-9]+:role/[0-9a-zA-Z\-_\.]+', user_input):
        raise argparse.ArgumentTypeError(
            'ARN provided is not formatted properly')
    return user_input


if __name__ == '__main__':
    # Logging setup
    logger = logging.getLogger('flashbulb.deploy')
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    parser = argparse.ArgumentParser()
    parser.add_argument('role_arn', type=parse_lambda_execution_role, help='Lambda execution role ARN to assign to Flashbulb lambda functions')
    parser.add_argument('regions', type=parse_regions, default="us-east-2",
                        help="A comma-separated list of AWS regions to distribute Flashbulb jobs.")
    
    check_credentials()
    config = parser.parse_args()
    deploy(config.regions, config.role_arn)
