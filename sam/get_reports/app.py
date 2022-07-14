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
    response = table.query(
        KeyConditionExpression=Key('pk').eq('reports')
    )
    # Return 404 if there are no reports in the database
    # boto3 does not include 'Items' in the response if there are no items. The
    # mock framework, moto3 DOES include Items, but as an empty array.
    if 'Items' not in response or len(response['Items']) == 0:
        return apigw_response(404)
    return_item = {x['sk']: {'name': x['name'], 'labels': x['labels']} for x in
                   response['Items']}
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
