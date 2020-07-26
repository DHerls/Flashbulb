import argparse
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from modules.deploy import deploy_regions
from modules.run import invoke_flashbulb
from modules.update import update_regions
from modules.destroy import destroy
import re
import logging

logger = logging.getLogger('flashbulb')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)

def parse_regions(region_string):
    """Return a list of valid regions from a comma-separated input string."""
    aws_ec2 = boto3.client('ec2')
    response = aws_ec2.describe_regions(
        Filters=[
            {
                'Name': 'opt-in-status',
                'Values': [
                    'opted-in',
                    'opt-in-not-required'
                ]
            }
        ]
    )
    valid_regions = {r['RegionName'] for r in response['Regions']}
    input_regions = {r.lower() for r in re.split(r',\s*', region_string)}
    invalid_regions = input_regions - valid_regions
    if invalid_regions:
        raise argparse.ArgumentTypeError(
            'The following regions are disabled for your account or do not exist: {}'.format(', '.join(invalid_regions)))
    return sorted(list(input_regions))


def parse_lambda_execution_role(user_input):
    if not re.match(r'arn:aws:iam::[0-9]+:role/[0-9a-zA-Z\-_\.]+', user_input):
        raise argparse.ArgumentTypeError(
            'ARN provided is not formatted properly')
    return user_input


def check_credentials():
    try:
        aws_lambda = boto3.client('lambda')
        aws_lambda.list_functions()
    except ClientError as e:
        logger.debug('Login error - HTTP {} - {}'.format(
            e.response['ResponseMetadata']['HTTPStatusCode'], e.response['Error']['Message']))
        logger.error("No valid AWS credentials found, exiting")
        exit(-1)
    except NoCredentialsError:
        logger.error("No valid AWS credentials found, exiting")
        exit(-1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    subparsers = parser.add_subparsers()

    run_parser = subparsers.add_parser('run', help='Run Flashbulb against a list of targets')
    run_parser.add_argument('target_list', type=open, help="File of targets to scan")
    run_parser.add_argument('bucket', help="S3 bucket to upload results")
    run_parser.add_argument('--regions', type=parse_regions, default="us-east-2", help="A comma-separated list of AWS regions to distribute Flashbulb jobs")
    run_parser.add_argument(
        '--prefix', default='', help="Prefix to add to filenames in the bucket. By default, files are placed in bucket root.")
    run_parser.add_argument('--skip-tests', action='store_true', help="Skip the initial test to ensure functions are working properly in each region")
    run_parser.add_argument('--http-and-https', action='store_true',
                            help="Try to visit every site over http and https")
    run_parser.set_defaults(func=invoke_flashbulb)
    
    deploy_parser = subparsers.add_parser('deploy', help='Deploy Flashbulb to your AWS instance in specified regions')
    deploy_parser.add_argument('role_arn', type=parse_lambda_execution_role, help='Lambda execution role ARN to assign to Flashbulb lambda functions')
    deploy_parser.add_argument('regions', type=parse_regions, default="us-east-2", help="A comma-separated list of AWS regions")
    deploy_parser.set_defaults(func=deploy_regions)

    update_parser = subparsers.add_parser('update', help='Update Flashbulb functions deployed to your AWS instance')
    update_parser.add_argument('regions', type=parse_regions, default="us-east-2", help="A comma-separated list of AWS regions")
    update_parser.set_defaults(func=update_regions)

    destroy_parser = subparsers.add_parser('destroy', help='Destroy Flashbulb functions deployed to your AWS instance')
    destroy_parser.add_argument('regions', type=parse_regions, default="us-east-2", help="A comma-separated list of AWS regions")
    destroy_parser.set_defaults(func=destroy)
    
    check_credentials()
    config = parser.parse_args()
    if config.debug:
        ch.setLevel(logging.DEBUG)
        logger.debug('Debug logs visible')

    config.func(config)
