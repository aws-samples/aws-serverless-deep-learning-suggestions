# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
from os import environ

import boto3
import simplejson as json
from boto3.dynamodb.conditions import Key
from loguru import logger


def lambda_handler(event, context):
    logger.debug('Event: ' + json.dumps(event))
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(environ['REPORT_TABLE'])
    status_filter = 'submitted'
    if 'status' in event['queryStringParameters']:
        status_filter = event['queryStringParameters']['status']
    if status_filter not in ('pending', 'submitted', 'resolved'):
        return apigw_response(400, 'Invalid submission filter. Submission '
                                   'filter must be one of pending, submitted,'
                                   ' or resolved.')
    response = table.query(
        IndexName='GSI1',
        KeyConditionExpression=Key('gsi1pk').eq(status_filter)
    )
    return apigw_response(200, response['Items'])


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
