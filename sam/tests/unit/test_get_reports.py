import json
import os
from unittest import mock

import boto3
import pytest
from moto import mock_dynamodb2

from sam.get_reports import app


@pytest.fixture()
def apigw_event():
    ''' Generates API GW Event'''

    return {
        'resource': '/reports',
        'path': '/reports',
        'httpMethod': 'GET',
        'pathParameters': {}
    }


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
    assert ret['statusCode'] == 404
    assert 'body' not in ret


@mock_dynamodb2
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_with_report(apigw_event):
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
            'pk': {'S': 'reports'},
            'sk': {'S': 'report-1'},
            'gsi1pk': {'S': 'report-1'},
            'gsi1sk': {'S': 'Damaged Fire Hydrant'},
            'labels': {
                'L': [
                    {'S': 'Fire Hydrant'},
                    {'S': 'Hydrant'}
                ]
            },
            'name': {'S': 'Damaged Fire Hydrant'}
        }
    )
    ret = app.lambda_handler(apigw_event, None)
    assert ret['statusCode'] == 200
    assert 'body' in ret
    ret_body = json.loads(ret['body'])
    assert 'report-1' in ret_body
    assert ret_body['report-1']['name'] == 'Damaged Fire Hydrant'
    assert 'Fire Hydrant' in ret_body['report-1']['labels']


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
