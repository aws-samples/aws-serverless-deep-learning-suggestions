import os
from unittest import mock

import boto3
import pytest
from moto import mock_dynamodb2

from sam.seed_ddb_data import app


@pytest.fixture()
def cloudformation_event():
    return {
        "RequestType": "Create",
        "ServiceToken": "REDACTED",
        "ResponseURL": "REDACTED",
        "StackId": "REDACTED",
        "RequestId": "REDACTED",
        "LogicalResourceId": "SeedDDBData",
        "ResourceType": "Custom::SeedDDBData",
        "ResourceProperties": {
            "ServiceToken": "REDACTED",
            "TableName": "TEST_REPORT_TABLE"
        }
    }


@mock_dynamodb2
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_seed_data(cloudformation_event):
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
    ret = app.seed_data(cloudformation_event, None)
    response = client.get_item(
        TableName=os.environ['REPORT_TABLE'],
        Key={
            'pk': {'S': 'reports'},
            'sk': {'S': 'report-1'}
        },
    )
    assert response['Item']['name']['S'] == 'Damaged Fire Hydrant'


@mock_dynamodb2
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_seed_data_with_existing_data(cloudformation_event):
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
    ret = app.seed_data(cloudformation_event, None)
    response = client.get_item(
        TableName=os.environ['REPORT_TABLE'],
        Key={
            'pk': {'S': 'reports'},
            'sk': {'S': 'report-0'}
        },
    )
    assert 'Item' not in response
