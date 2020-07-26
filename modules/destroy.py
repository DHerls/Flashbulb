import asyncio
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger('flashbulb.destroy')

async def destroy_region(region):
    aws_cloudformation = boto3.client('cloudformation', region_name=region)
    logger.info("Destroying Flashbulb in {}".format(region))
    aws_cloudformation.delete_stack(StackName='Flashbulb')
    try:
        while True:
            aws_cloudformation.describe_stacks(StackName='Flashbulb')
            await asyncio.sleep(5)
    except ClientError:
        logger.info("Flashbulb destroyed in {}".format(region))



async def destroy_regions(options):
    tasks = []
    for region in options.regions:
        tasks.append(asyncio.create_task(destroy_region(region)))
    for t in tasks:
        await t

def destroy(options):
    asyncio.run(destroy_regions(options))
