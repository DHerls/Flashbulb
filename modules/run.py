from common.constants import FUNCTIONS, LAYERS
from common.utils import check_function, check_layer, get_function_name, get_user_response
import boto3
import json
import ipaddress
from urllib.parse import urlparse, urlunparse
import time
import uuid
import logging


logger = logging.getLogger('flashbulb.run')


def parse_host(line, http_and_https):
    """Return a list of valid hosts given a line containing a URL, IP address, or CIDR."""
    hosts = []

    try:
        network = ipaddress.ip_network(line)
        for ip in network.hosts():
            if http_and_https:
                hosts.append('https://' + ip.exploded)
            hosts.append('http://' + ip.exploded)
        return hosts
    except ValueError:
        # Line is not a CIDR address, continue as normal
        pass

    if line.find('://') == -1:
        line = 'http://' + line

    if http_and_https:
        url = urlparse(line)
        url = url._replace(scheme='http')
        hosts.append(urlunparse(url))
        url = url._replace(scheme='https')
        hosts.append(urlunparse(url))
    else:
        hosts.append(line)

    return hosts

def check_regions(regions, bucket, skip_tests):
    for region in regions:
        logger.info("Checking region {} settings".format(region))
        for key in LAYERS.keys():
            if not check_layer(key, region):
                logger.error(
                    "{0} layer in region {1} is out of date. Try running ./update with region {1}".format(key.title(), region))
                exit(-1)
        for key in FUNCTIONS.keys():
            if not check_function(key, region):
                logger.error(
                    "{0} function in region {1} is out of date. Try running ./update with region {1}".format(key.title(), region))
                exit(-1)

        if not skip_tests:
            if not test_screenshot(region, bucket):
                logger.error(
                    "Screenshot function does not appear to be working in {}. Check CloudWatch logs for more information.".format(region))
                exit(-1)


def invoke_screenshot(region, url, bucket, prefix):
    aws_lambda = boto3.client('lambda', region_name=region)
    response = aws_lambda.invoke(
        FunctionName=get_function_name('screenshot'),
        InvocationType='Event',
        Payload=json.dumps({'url': url, 'bucket': bucket,
                            'prefix': prefix}).encode('utf-8')
    )


def invoke_flashbulb(options):
    if options.prefix.startswith('/'):
        options.prefix = options.prefix[1:]
    if not options.prefix.endswith('/') and len(options.prefix) > 0:
        options.prefix += '/'

    logger.info("Flashbulb is warming up.")

    hosts = []
    for line in options.target_list.readlines():
        line = line.strip()
        if not line:
            continue
        hosts.extend(parse_host(line, options.http_and_https))
    user_input = get_user_response(
        'Flashbulb found {} potential targets. Continue? (y/N)'.format(len(hosts)), ['y', 'n'], 'n')
    if user_input == 'n':
        exit(0)

    # Dedupe
    hosts = list(set(hosts))

    if options.skip_tests:
        logger.warning("Skipping active screenshot function tests.")
    check_regions(options.regions, options.bucket, options.skip_tests)
    logger.info("Checks complete. Safety goggles on!")

    num_regions = len(options.regions)
    for i, url in enumerate(hosts):
        invoke_screenshot(
            options.regions[i % num_regions], url, options.bucket, options.prefix)

    wait_for_completion(options.bucket, options.prefix, len(hosts))


def get_object_count(bucket, prefix):
    """Return the total number of objects with the given prefix in the given bucket."""
    aws_s3 = boto3.client('s3')
    response = aws_s3.list_objects_v2(
        Bucket=bucket,
        Prefix=prefix
    )
    total_objects = response['KeyCount']
    while response['IsTruncated']:
        response = aws_s3.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            ContinuationToken=response['NextContinuationToken']
        )
        total_objects += response['KeyCount']
    return total_objects


def wait_for_completion(bucket, prefix, num_targets, silent=False):
    timeout = 120
    start = time.time()
    while time.time() - start < timeout:
        total_objects = get_object_count(bucket, prefix)
        errors = get_object_count(bucket, prefix + 'errors')
        successes = (total_objects - errors) // 2
        if not silent:
            logger.info('Status: {} successful, {} errored, {} remaining'.format(
                successes, errors, num_targets - successes - errors))
        if successes + errors < num_targets:
            time.sleep(5)
        else:
            if not silent:
                logger.info("All targets accounted for")
            return True
    if not silent:
        logger.error(
            "Timeout while waiting for target completion. Some may have failed.")
    return False


def test_screenshot(region, bucket):
    """Test screenshot lambda is working and can upload to the specified bucket"""
    prefix = str(uuid.uuid4()) + "/"
    invoke_screenshot(region, 'https://example.com', bucket, prefix)
    result = wait_for_completion(bucket, prefix, 1, True)
    if result:
        aws_s3 = boto3.client('s3')
        aws_s3.delete_object(Bucket=bucket, Key=prefix +
                             'https-example.com.png')
        aws_s3.delete_object(Bucket=bucket, Key=prefix +
                             'https-example.com.json')
    return result
