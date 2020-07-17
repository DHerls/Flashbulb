import logging
import argparse

from common.constants import CHROMIUM_LAYER_NAME, CHROMIUM_LAYER_VERSION, CHROMIUM_S3_KEY, FLASHBULB_BUCKET_PREFIX, SCREENSHOT_LAMBDA_NAME, SCREENSHOT_LAMBDA_VERSION, SCREENSHOT_S3_KEY
from common.utils import SemanticVersion, check_chromium_layer, check_credentials, check_screenshot_lambda, get_lambda_by_name, get_layer_by_name, parse_regions
import boto3

# Logging setup
logger = logging.getLogger('flashbulb.deploy')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)


def update_chromium_layer(region):
    logger.info("Updating Chromium layer in {}".format(region))
    aws_lambda = boto3.client('lambda', region_name=region)
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
    aws_lambda.update_function_configuration(
        FunctionName=SCREENSHOT_LAMBDA_NAME,
        Layers=[
            response['LayerVersionArn']
        ]
    )


def update_screenshot_lambda_code(region):
    logger.info("Updating screenshot function in {}".format(region))
    aws_lambda = boto3.client('lambda', region_name=region)
    aws_lambda.update_function_code(
        FunctionName=SCREENSHOT_LAMBDA_NAME,
        S3Bucket=FLASHBULB_BUCKET_PREFIX + region,
        S3Key=SCREENSHOT_S3_KEY
    )
    aws_lambda.update_function_configuration(
        FunctionName=SCREENSHOT_LAMBDA_NAME,
        Description=str(SCREENSHOT_LAMBDA_VERSION)
    )


def update_region(region):
    chromium_current = check_chromium_layer(region)
    screenshot_current = check_screenshot_lambda(region)
    if chromium_current and screenshot_current:
        logger.info("{region} already up to date".format(region=region))
        return
    if not chromium_current:
        update_chromium_layer(region)
    if not screenshot_current:
        update_screenshot_lambda_code(region)
    

def update(regions):
    for region in regions:
        update_region(region)

if __name__ == '__main__':
    

    parser = argparse.ArgumentParser()
    parser.add_argument('regions', type=parse_regions, default="us-east-2",
                        help="A comma-separated list of AWS regions to distribute Flashbulb jobs.")

    check_credentials()
    config = parser.parse_args()
    update(config.regions)
