# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import re
from os import environ

import boto3
import simplejson as json
from loguru import logger


def lambda_handler(event, context):
    logger.debug('Event: ' + json.dumps(event))
    # Make sure it's a UUIDv4 submission id
    path_regex = r"(?P<submission_id>[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12})"
    path_matches = re.match(path_regex,
                            event['pathParameters']['submission_id'])
    if path_matches:
        submission_id = path_matches.group('submission_id')
    else:
        submission_id = None
    if not submission_id:
        logger.error(
            'Unrecognized Path: ' + json.dumps(event['pathParameters']))
        return apigw_response(400,
                              'Invalid submissions_id. Submission ID must be UUIDv4 format.')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(environ['REPORT_TABLE'])
    response = table.get_item(
        Key={
            'pk': f"submission_{submission_id}",
            'sk': f"submission_{submission_id}",
        }
    )
    if 'Item' not in response or len(response['Item']) == 0:
        return apigw_response(404)
    return_item = response['Item']
    return_item['status'] = return_item['gsi1pk']
    del return_item['gsi1pk']
    del return_item['gsi1sk']
    return apigw_response(200, return_item)


def apigw_response(status_code, body=None):
    response = {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Origin': environ['ALLOW_ORIGIN_HEADER_VALUE'],
            'Access-Control-Allow-Methods': 'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT'
        }
    }
    if body:
        response['body'] = body if isinstance(body, str) else json.dumps(body)
    return response
