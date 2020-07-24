import argparse
import logging
from common.constants import FUNCTIONS, LAYERS, FLASHBULB_DIR, FLASHBULB_BUCKET_PREFIX
from common.utils import get_function_by_key, get_function_name, get_function_s3_key, get_layer_name, get_layer_s3_key
import re
import boto3
import time
import asyncio

logger = logging.getLogger('flashbulb.deploy')

async def deploy_region(region, role_arn):
    aws_cloudformation = boto3.client('cloudformation', region_name=region)
    if len(aws_cloudformation.describe_stacks(StackName='Flashbulb')['Stacks']) != 0:
        logger.warning("Flashbulb already deployed in {}, try updating instead.".format(region))
        return

    logger.info("Deploying Flashbulb in {}".format(region))
    template_path = FLASHBULB_DIR.joinpath('assets').joinpath('cloudformation_template.json')
    with open(template_path, 'r') as f:
        template_body = f.read()

    response = aws_cloudformation.create_stack(
        StackName='Flashbulb',
        TemplateBody=template_body,
        Parameters=[
            {
                'ParameterKey': 'ChromiumVersion',
                'ParameterValue': str(LAYERS['chromium']['version']),
            },
            {
                'ParameterKey': 'WappalyzerVersion',
                'ParameterValue': str(LAYERS['wappalyzer']['version']),
            },
            {
                'ParameterKey': 'ScreenshotVersion',
                'ParameterValue': str(FUNCTIONS['screenshot']['version']),
            },
            {
                'ParameterKey': 'AnalyzeVersion',
                'ParameterValue': str(FUNCTIONS['analyze']['version']),
            },
            {
                'ParameterKey': 'LambdaRoleArn',
                'ParameterValue': role_arn,
            },
        ],
        ResourceTypes=[
            'AWS::Lambda::*',
        ]
    )

    stack_status = 'CREATE_IN_PROGRESS'
    while stack_status == 'CREATE_IN_PROGRESS':
        await asyncio.sleep(5)
        response = aws_cloudformation.describe_stacks(StackName='Flashbulb')
        stack_status = response['Stacks'][0]['StackStatus']
    
    if stack_status == 'CREATE_COMPLETE':
        logger.info("Successfully deployed Flashbulb in {}".format(region))
    else:
        logger.error("Error deploying Flashbulb in {}, status {}".format(region, stack_status))


async def deploy_async(options):
    tasks = []
    for region in options.regions:
        tasks.append(asyncio.create_task(deploy_region(region, options.role_arn)))
    for task in tasks:
        await task
    logger.info('Done deploying Flashbulb across {} region{}'.format(
        len(options.regions), 's' if len(options.regions) > 1 else ''))


def deploy_regions(options):
    asyncio.run(deploy_async(options))
