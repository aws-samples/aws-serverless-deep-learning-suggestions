# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import re
from datetime import datetime
from decimal import Decimal
from os import environ

import boto3
import simplejson as json
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from loguru import logger


def lambda_handler(event, context):
    logger.debug('Event: ' + json.dumps(event))
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
    try:
        body = json.loads(event['body'])
    except ValueError:
        logger.error('Unrecognized Patch Format: ' + event['body'])
        return apigw_response(400,
                              'Invalid patch format. Must have an JSON body.')
    if 'action' not in body:
        logger.error('Unrecognized Patch Format: ' + json.dumps(body))
        return apigw_response(400,
                              'Invalid patch format. Must have an action attribute.')
    if body['action'] == 'submit':
        selected_reports = []
        for report in body['selected_reports']:
            if report.startswith('report-'):
                selected_reports.append(report)
        coords_browser = {
            'latitude': 0,
            'longitude': 0
        }
        if 'coords' in body:
            if 'latitude' in body['coords'] and 'longitude' in body['coords']:
                coords_browser = {
                    'latitude': Decimal(body['coords']['latitude']).quantize(
                        Decimal("1.000000000000000")),
                    'longitude': Decimal(body['coords']['longitude']).quantize(
                        Decimal("1.000000000000000"))
                }
        try:
            updated_item = table.update_item(
                Key={
                    'pk': f"submission_{submission_id}",
                    'sk': f"submission_{submission_id}"
                },
                UpdateExpression='SET selected_reports = :selected_reports, coords_browser = :coords_browser, gsi1pk = :gsi1pk, timestamp_submitted = :timestamp_submitted',
                ExpressionAttributeValues={
                    ':selected_reports': selected_reports,
                    ':coords_browser': coords_browser,
                    ':gsi1pk': 'submitted',
                    ':timestamp_submitted': datetime.utcnow().isoformat()[
                                            :-3] + 'Z'
                },
                ReturnValues='ALL_NEW',
                ConditionExpression=Attr('pk').eq(f"submission_{submission_id}")
            )
        except ClientError as e:
            # ConditionExpression of update_item ensures that we only update
            # an existing resource, instead of creating a new one, like
            # update_item will do by default.
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.error('Submission ID Not Found: ' + submission_id)
                return apigw_response(404, 'Submission ID Not Found')
        return_item = updated_item['Attributes']
        return_item['status'] = return_item['gsi1pk']
        del return_item['gsi1pk']
        del return_item['gsi1sk']
        return apigw_response(200, return_item)
    elif body['action'] == 'resolve':
        try:
            table.update_item(
                Key={
                    'pk': f"submission_{submission_id}",
                    'sk': f"submission_{submission_id}"
                },
                UpdateExpression='SET gsi1pk = :gsi1pk, timestamp_resolved = :timestamp_resolved',
                ExpressionAttributeValues={
                    ':gsi1pk': 'resolved',
                    ':timestamp_resolved': datetime.utcnow().isoformat()[
                                           :-3] + 'Z'
                },
                ConditionExpression=Attr('pk').eq(f"submission_{submission_id}")
            )
        except ClientError as e:
            # ConditionExpression of update_item ensures that we only update
            # an existing resource, instead of creating a new one, like
            # update_item will do by default.
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.error('Submission ID Not Found: ' + submission_id)
                return apigw_response(404, 'Submission ID Not Found')
        return apigw_response(204)


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
