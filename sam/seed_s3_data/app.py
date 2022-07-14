# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import mimetypes
import os
import zipfile

import boto3
import simplejson as json
from crhelper import CfnResource
from loguru import logger

helper = CfnResource()


@helper.create
def seed_data(event, _):
    logger.debug('Event: ' + json.dumps(event))
    logger.debug(f"Retrieving S3 Static Website Contents...")
    s3 = boto3.client('s3')
    response = s3.list_objects_v2(
        Bucket=event['ResourceProperties']['StaticWebsiteBucket'],
        MaxKeys=1
    )
    if response['KeyCount'] > 0:
        # Static Website Bucket already has contents, skipping
        return
    with zipfile.ZipFile('website.zip', 'r') as zip_ref:
        zip_ref.extractall('/tmp/website/')
    path = '/tmp/website/website'
    # Replace placeholder config values with Lambda inputs
    config_path = os.path.join(path, 'js/config.js')
    logger.debug(f"Modifying Website Config {config_path}...")
    with open(config_path, 'r') as file:
        config_data = file.read()
    config_data = config_data.replace('REPLACE_ME_IDENTITY_POOL_ID',
                                      event['ResourceProperties'][
                                          'IdentityPoolId'])
    config_data = config_data.replace('REPLACE_ME_UNIQUE_SUFFIX',
                                      event['ResourceProperties'][
                                          'UniqueSuffix'])
    config_data = config_data.replace('REPLACE_ME_API_BASE_URL',
                                      event['ResourceProperties']['ApiBaseURL'])
    with open(config_path, 'w') as file:
        file.write(config_data)
    # Upload the website data
    logger.debug(f"Uploading Website Data...")
    for subdir, dirs, files in os.walk(path):
        for file in files:
            full_path = os.path.join(subdir, file)
            with open(full_path, 'rb') as data:
                object_key = full_path[len(path) + 1:]
                logger.debug(
                    f"Uploading: {full_path} -> s3://{event['ResourceProperties']['StaticWebsiteBucket']}/{object_key}")
                s3.put_object(
                    Bucket=event['ResourceProperties']['StaticWebsiteBucket'],
                    Key=object_key,
                    Body=data,
                    ContentType=mimetypes.guess_type(full_path)[0]
                )


@helper.delete
def delete_data(event, _):
    logger.debug('Event: ' + json.dumps(event))
    s3 = boto3.client('s3')
    bucket_list = [
        event['ResourceProperties']['StaticWebsiteBucket'],
        event['ResourceProperties']['UploadedImagesBucket']
    ]
    for bucket in bucket_list:
        logger.debug(f"Deleting S3 Bucket Contents: {bucket}")
        key_count = 1
        while key_count > 0:
            response = s3.list_objects_v2(
                Bucket=bucket,
                MaxKeys=1000
            )
            key_count = response['KeyCount']
            if key_count > 0:
                delete_dict = [{'Key': x['Key']} for x in response['Contents']]
                for key_obj in delete_dict:
                    logger.debug(
                        f"Queueing S3 Object Deletion: {key_obj['Key']}")
                s3.delete_objects(
                    Bucket=bucket,
                    Delete={'Objects': delete_dict}
                )


@helper.update
def no_op(_, __):
    # No Operation
    pass


def handler(event, context):
    helper(event, context)
