import argparse
import logging
from common.constants import CHROMIUM_LAYER_NAME, CHROMIUM_LAYER_VERSION, CHROMIUM_S3_KEY, FLASHBULB_BUCKET_PREFIX, SCREENSHOT_LAMBDA_NAME, SCREENSHOT_LAMBDA_VERSION, SCREENSHOT_S3_KEY
from common.utils import check_credentials, get_lambda_by_name, get_layer_by_name, parse_regions
import re
import boto3


def deploy_chromium_layer(region):
    """Attempt to auto-setup headless chromium lambda layer in the given region"""
    aws_lambda = boto3.client('lambda', region_name=region)
    logger.info("Deploying Chromium layer in {}".format(region))
    response = aws_lambda.publish_layer_version(
        LayerName=CHROMIUM_LAYER_NAME,
        Description=str(CHROMIUM_LAYER_VERSION),
        Content={
            'S3Bucket': FLASHBULB_BUCKET_PREFIX + region,
            'S3Key': CHROMIUM_S3_KEY
        },
        CompatibleRuntimes=[
            'nodejs10.x', 'nodejs12.x'
        ],
    )
    return response


def deploy_screenshot_lambda(region, role_arn):
    chromium_layer = deploy_chromium_layer(region)
    logger.info("Deploying lambda function in {}".format(region))
    aws_lambda = boto3.client('lambda', region_name=region)
    aws_lambda.create_function(
        FunctionName=SCREENSHOT_LAMBDA_NAME,
        Runtime='nodejs12.x',
        Role=role_arn,
        Handler='index.handler',
        Code={
            'S3Bucket': FLASHBULB_BUCKET_PREFIX + region,
            'S3Key': SCREENSHOT_S3_KEY
        },
        Description=str(SCREENSHOT_LAMBDA_VERSION),
        Timeout=300,
        MemorySize=2048,
        Publish=True,
        Layers=[
            chromium_layer['LayerVersionArn']
        ]
    )


def deploy_region(region, role_arn):
    screenshot_function = get_lambda_by_name(SCREENSHOT_LAMBDA_NAME, region)
    if screenshot_function is not None:
        logger.info("Region {} already deployed, skipping".format(region))
    else:
        deploy_screenshot_lambda(region, role_arn)


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
