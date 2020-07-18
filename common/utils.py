import re
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging
import argparse

from .constants import LAYERS, FUNCTIONS, SemanticVersion

# Logging setup
logger = logging.getLogger('flashbulb.utils')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)


def check_credentials():
    try:
        iam = boto3.resource('iam')
        current_user = iam.CurrentUser()
        logger.debug('Flashbulb logged into AWS as {username}'.format(
            username=current_user.user_name))
    except ClientError as e:
        logger.debug('Login error - HTTP {} - {}'.format(
            e.response['ResponseMetadata']['HTTPStatusCode'], e.response['Error']['Message']))
        logger.error("No valid AWS credentials found, exiting")
        exit(-1)
    except NoCredentialsError:
        logger.error("No valid AWS credentials found, exiting")
        exit(-1)


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

def get_user_response(message, options, default=None):
    """Return an option the user selected from a list of available options."""
    prompt = '{} > '.format(message)
    userinput = input(prompt)
    while True:
        if userinput.lower() in options:
            return userinput.lower()
        elif default is not None and userinput.strip() == '':
            return default
        else:
            print("Please select a valid option.")
            userinput = input(prompt)


def _list_lambda_functions(region):
    aws_lambda = boto3.client('lambda', region_name=region)
    marker = None
    while True:
        # Boto3 is dumb and will not allow default values
        if marker is None:
            response = aws_lambda.list_functions()
        else:
            response = aws_lambda.list_functions(Marker=marker)

        yield from response['Functions']
        if 'NextMarker' in response:
            marker = response['NextMarker']
        else:
            break


def get_function_by_key(key, region):
    """Return a lambda function with the given name or None if it does not exist."""
    expected_name = get_function_name(key)
    for function in _list_lambda_functions(region):
        if function['FunctionName'] == expected_name:
            return function
    return None


def _list_lambda_layers(region):
    aws_lambda = boto3.client('lambda', region_name=region)
    marker = None
    while True:
        # Boto3 is dumb and will not allow default values
        if marker is None:
            response = aws_lambda.list_layers()
        else:
            response = aws_lambda.list_layers(Marker=marker)

        yield from response['Layers']
        if 'NextMarker' in response:
            marker = response['NextMarker']
        else:
            break


def get_layer_by_key(key, region):
    """Return the ARN of a lambda layer with the given name or None if it does not exist."""
    expected_name = get_layer_name(key)
    for layer in _list_lambda_layers(region):
        if layer['LayerName'] == expected_name:
            return layer
    return None


def check_function(key, region):
    function = get_function_by_key(key, region)
    if function is None:
        logger.error(
            "Cannot find {function} function in {region}. Try running ./deploy for region {region}".format(region=region, function=key.title()))
        exit(-1)
    version = SemanticVersion(function['Description'])
    if version == FUNCTIONS[key]['version']:
        return True
    if version < FUNCTIONS[key]['version']:
        return False

    logger.error(
        "{function} function in {region} has unknown version number. Update Flashbulb code and try again.".format(region=region, function=key.title()))
    exit(-1)


def check_layer(key, region):
    layer = get_layer_by_key(key, region)
    if layer is None:
        logger.error(
            "Cannot find {layer} layer in {region}. Try running ./deploy for region {region}".format(region=region, layer=key.title()))
        exit(-1)
    version = SemanticVersion(layer['LatestMatchingVersion']['Description'])
    if version == LAYERS[key]['version']:
        return True
    if version < LAYERS[key]['version']:
        return False
    
    logger.error(
        "{layer} layer in {region} has unknown version number. Update Flashbulb code and try again.".format(region=region, layer=key.title()))
    exit(-1)


def get_layer_s3_key(key):
    return "{}/{}/layer.zip".format(key, str(LAYERS[key]['version']))


def get_layer_name(key):
    return "Flashbulb--" + key.title()


def get_function_s3_key(key):
    return "{}/{}/function.zip".format(key, str(FUNCTIONS[key]['version']))


def get_function_name(key):
    return "Flashbulb--" + key.title()
