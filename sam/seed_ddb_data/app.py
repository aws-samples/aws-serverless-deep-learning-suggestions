# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import os

import boto3
import simplejson as json
from boto3.dynamodb.conditions import Key
from crhelper import CfnResource
from loguru import logger

helper = CfnResource()


@helper.create
def seed_data(event, _):
    logger.debug('Event: ' + json.dumps(event))
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(event['ResourceProperties']['TableName'])
    logger.debug(f"Retrieving Reportable Options...")
    response = table.query(
        KeyConditionExpression=Key('pk').eq('reports')
    )
    if response['Count'] > 0:
        logger.debug(f"Reports already exist in the table. Exiting.")
        return
    with table.batch_writer() as batch:
        file_path = os.path.join(os.path.dirname(__file__), 'initial_data.json')
        with open(file_path) as f:
            initial_data = json.load(f)
            for item in initial_data:
                logger.debug(
                    f"Writing Item to Table... PK: {item['pk']} | SK: {item['sk']}")
                batch.put_item(Item=item)


@helper.update
@helper.delete
def no_op(_, __):
    # No Operation
    pass


def handler(event, context):
    helper(event, context)
