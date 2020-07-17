"""Developer function to upload copies of a zip file across every region."""

import boto3
import argparse

def global_upload(file, dest):
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
    region_names = [r['RegionName'] for r in response['Regions']]

    r1 = region_names[0]
    s3 = boto3.resource('s3')
    print('Uploading to {}...'.format(r1), end='', flush=True)
    s3.Object('flashbulb-' + r1, dest).upload_file(file)
    print('Done')

    for region in region_names[1:]:
        print('Copying to {}...'.format(region), end='', flush=True)
        s3.Object('flashbulb-'+region, dest).copy_from(CopySource='flashbulb-'+r1+'/'+dest)
        print('Done')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('dest')

    config = parser.parse_args()
    global_upload(config.file, config.dest)
