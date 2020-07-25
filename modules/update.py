import logging
import argparse

from common.constants import  FLASHBULB_DIR, ENTITIES
from common.utils import SemanticVersion,check_function, check_layer, get_function_name, get_function_s3_key, get_layer_name, get_layer_s3_key
import boto3
import asyncio
from botocore.exceptions import ClientError


logger = logging.getLogger('flashbulb.update')


async def update_region(region):
    aws_cloudformation = boto3.client('cloudformation', region_name=region)
    try:
        stack = aws_cloudformation.describe_stacks(StackName='Flashbulb')['Stacks'][0]
        needs_update = False
        role_arn = None
        for p in stack['Parameters']:
            if p['ParameterKey'] == 'LambdaRoleArn':
                role_arn = p['ParameterValue']
                continue
            if 'Version' not in p['ParameterKey']:
                continue
            key = p['ParameterKey'].replace('Version', '').lower()
            aws_version = SemanticVersion(p['ParameterValue'])
            if aws_version < ENTITIES[key]['version']:
                needs_update = True
                # Don't break because we need to find LambdaRoleArn
            elif aws_version > ENTITIES[key]['version']:
                logger.error("Flashbulb does not recognize deployed version. Please update Flashbulb code.")
        if not needs_update:
            logger.info("Flashbulb in {} is already up to date".format(region))
            return
        
        logger.info("Updating Flashbulb in {}".format(region))
        template_path = FLASHBULB_DIR.joinpath('assets').joinpath('cloudformation_template.json')
        with open(template_path, 'r') as f:
            template_body = f.read()

        response = aws_cloudformation.update_stack(
            StackName='Flashbulb',
            TemplateBody=template_body,
            UsePreviousTemplate=False,
            Parameters=[
                {
                    'ParameterKey': 'ChromiumVersion',
                    'ParameterValue': str(ENTITIES['chromium']['version']),
                },
                {
                    'ParameterKey': 'WappalyzerVersion',
                    'ParameterValue': str(ENTITIES['wappalyzer']['version']),
                },
                {
                    'ParameterKey': 'ScreenshotVersion',
                    'ParameterValue': str(ENTITIES['screenshot']['version']),
                },
                {
                    'ParameterKey': 'AnalyzeVersion',
                    'ParameterValue': str(ENTITIES['analyze']['version']),
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

        stack_status = 'UPDATE_IN_PROGRESS'
        while stack_status == 'UPDATE_IN_PROGRESS':
            await asyncio.sleep(5)
            response = aws_cloudformation.describe_stacks(StackName='Flashbulb')
            stack_status = response['Stacks'][0]['StackStatus']
        
        if stack_status == 'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS' or stack_status == 'UPDATE_COMPLETE':
            logger.info("Successfully updated Flashbulb in {}".format(region))
        else:
            logger.error("Error updating Flashbulb in {}, status {}".format(region, stack_status))
            
    except ClientError:
        # Stack doesn't exist
        logger.warning("Flashbulb not found in {}. Try deploying instead.".format(region))
        return


async def update_async(options):
    tasks = []
    for region in options.regions:
        tasks.append(asyncio.create_task(update_region(region)))
    for task in tasks:
        await task
    logger.info('Done updating Flashbulb across {} region{}'.format(
        len(options.regions), 's' if len(options.regions) > 1 else ''))


def update_regions(options):
    asyncio.run(update_async(options))