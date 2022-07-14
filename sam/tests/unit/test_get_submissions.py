import json
import os
from unittest import mock

import boto3
import pytest
from moto import mock_dynamodb2

from sam.get_submissions import app


@pytest.fixture()
def apigw_event():
    ''' Generates API GW Event'''

    return {
        "resource": "/submissions",
        "path": "/submissions",
        "httpMethod": "GET",
        "queryStringParameters": {
            "status": "submitted"
        }
    }


@pytest.fixture()
def apigw_event_bad_status():
    ''' Generates API GW Event'''

    return {
        "resource": "/submissions",
        "path": "/submissions",
        "httpMethod": "GET",
        "queryStringParameters": {
            "status": "bad_status_here"
        }
    }


@mock_dynamodb2
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_bad_status(apigw_event_bad_status):
    ret = app.lambda_handler(apigw_event_bad_status, None)
    assert ret['statusCode'] == 400
    assert ret[
               'body'] == 'Invalid submission filter. Submission filter must be one of pending, submitted, or resolved.'


@mock_dynamodb2
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_no_reports(apigw_event):
    boto3.setup_default_session()
    client = boto3.client('dynamodb', region_name='us-west-2')
    client.create_table(
        TableName='TEST_REPORT_TABLE',
        KeySchema=[
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'GSI1',
                'KeySchema': [
                    {'AttributeName': 'gsi1pk', 'KeyType': 'HASH'},
                    {'AttributeName': 'gsi1sk', 'KeyType': 'RANGE'},
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
            {'AttributeName': 'gsi1pk', 'AttributeType': 'S'},
            {'AttributeName': 'gsi1sk', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    ret = app.lambda_handler(apigw_event, None)
    assert ret['statusCode'] == 200
    assert 'body' not in ret


@mock_dynamodb2
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_with_reports(apigw_event):
    boto3.setup_default_session()
    client = boto3.client('dynamodb', region_name='us-west-2')
    client.create_table(
        TableName='TEST_REPORT_TABLE',
        KeySchema=[
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'GSI1',
                'KeySchema': [
                    {'AttributeName': 'gsi1pk', 'KeyType': 'HASH'},
                    {'AttributeName': 'gsi1sk', 'KeyType': 'RANGE'},
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
            {'AttributeName': 'gsi1pk', 'AttributeType': 'S'},
            {'AttributeName': 'gsi1sk', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    client.put_item(
        TableName='TEST_REPORT_TABLE',
        Item={
            'pk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'},
            'sk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'},
            'coords_image': {
                'M': {
                    'latitude': {'N': '33.718811100000003'},
                    'longitude': {'N': '-112.174887900000002'}
                }
            },
            'gsi1pk': {'S': 'submitted'},
            'gsi1sk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'},
            'ml_labels': {
                'M': {
                    'Fire Hydrant': {'N': '72.792'},
                    'Hydrant': {'N': '87.938'}
                }
            },
            'relevant_reports': {
                'M': {
                    'report-1': {'N': '160.73'}
                }
            },
            'selected_reports': {
                'L': [{'S': 'report-1'}]
            },
            'timestamp_submitted': {'S': '2022-06-07T18:57:16.564Z'}
        }
    )
    ret = app.lambda_handler(apigw_event, None)
    assert ret['statusCode'] == 200
    assert 'body' in ret
    ret_body = json.loads(ret['body'])
    assert 'timestamp_submitted' in ret_body[0]


@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_apigw_response_no_body():
    ret = app.apigw_response(200, body=None)
    assert ret['statusCode'] == 200
    assert ret['headers'][
               'Access-Control-Allow-Headers'] == 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'
    assert ret['headers']['Access-Control-Allow-Origin'] == 'TEST_HEADER_VALUE'
    assert ret['headers'][
               'Access-Control-Allow-Methods'] == 'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT'
    assert 'body' not in ret


@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_apigw_response_with_body():
    ret = app.apigw_response(200, body={'key': 'value'})
    assert ret['statusCode'] == 200
    assert ret['headers'][
               'Access-Control-Allow-Headers'] == 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'
    assert ret['headers']['Access-Control-Allow-Origin'] == 'TEST_HEADER_VALUE'
    assert ret['headers'][
               'Access-Control-Allow-Methods'] == 'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT'
    assert ret['body'] == '{"key": "value"}'
