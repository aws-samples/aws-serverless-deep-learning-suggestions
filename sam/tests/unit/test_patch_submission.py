import json
import os
from unittest import mock

import boto3
import pytest
from moto import mock_dynamodb

from sam.patch_submission import app


@pytest.fixture()
def apigw_event():
    ''' Generates API GW Event'''

    return {
        "resource": "/api/submission/{submission_id}",
        "path": "/api/submission/97cc0239-34fc-49d1-b87a-eb226ecc0e81",
        "httpMethod": "PATCH",
        "pathParameters": {
            "submission_id": "97cc0239-34fc-49d1-b87a-eb226ecc0e81"
        },
        "body": "{\"action\":\"submit\",\"selected_reports\":[\"report-1\"],\"coords\":{\"latitude\":33.7188152,\"longitude\":-112.1748911}}"
    }


@pytest.fixture()
def apigw_event_resolve():
    ''' Generates API GW Event'''

    return {
        "resource": "/api/submission/{submission_id}",
        "path": "/api/submission/97cc0239-34fc-49d1-b87a-eb226ecc0e81",
        "httpMethod": "PATCH",
        "pathParameters": {
            "submission_id": "97cc0239-34fc-49d1-b87a-eb226ecc0e81"
        },
        "body": "{\"action\":\"resolve\"}"
    }


@pytest.fixture()
def apigw_event_bad_submission_id():
    ''' Generates API GW Event'''

    return {
        "resource": "/api/submission/{submission_id}",
        "path": "/api/submission/70b2a1e7",
        "httpMethod": "PATCH",
        "pathParameters": {
            "submission_id": "70b2a1e7"
        },
        "body": "{\"action\":\"submit\",\"selected_reports\":[\"report-1\"],\"coords\":{\"latitude\":33.7188152,\"longitude\":-112.1748911}}"
    }


@pytest.fixture()
def apigw_event_bad_body():
    ''' Generates API GW Event'''

    return {
        "resource": "/api/submission/{submission_id}",
        "path": "/api/submission/97cc0239-34fc-49d1-b87a-eb226ecc0e81",
        "httpMethod": "PATCH",
        "pathParameters": {
            "submission_id": "97cc0239-34fc-49d1-b87a-eb226ecc0e81"
        },
        "body": "{\"malformed\"}"
    }


@pytest.fixture()
def apigw_event_invalid_body():
    ''' Generates API GW Event'''

    return {
        "resource": "/api/submission/{submission_id}",
        "path": "/api/submission/97cc0239-34fc-49d1-b87a-eb226ecc0e81",
        "httpMethod": "PATCH",
        "pathParameters": {
            "submission_id": "97cc0239-34fc-49d1-b87a-eb226ecc0e81"
        },
        "body": "{\"no-action\": \"but well formed\"}"
    }


@mock_dynamodb
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_bad_submission_id(apigw_event_bad_submission_id):
    ret = app.lambda_handler(apigw_event_bad_submission_id, None)
    assert ret['statusCode'] == 400
    assert ret[
               'body'] == 'Invalid submissions_id. Submission ID must be UUIDv4 format.'


@mock_dynamodb
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_bad_body(apigw_event_bad_body):
    ret = app.lambda_handler(apigw_event_bad_body, None)
    assert ret['statusCode'] == 400
    assert ret['body'] == 'Invalid patch format. Must have an JSON body.'


@mock_dynamodb
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_invalid_body(apigw_event_invalid_body):
    ret = app.lambda_handler(apigw_event_invalid_body, None)
    assert ret['statusCode'] == 400
    assert ret['body'] == 'Invalid patch format. Must have an action attribute.'


@mock_dynamodb
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_submit_no_reports(apigw_event):
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
    assert ret['body'] == 'Submission ID Not Found'


@mock_dynamodb
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_resolve_no_reports(apigw_event_resolve):
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
    ret = app.lambda_handler(apigw_event_resolve, None)
    assert ret['statusCode'] == 404
    assert ret['body'] == 'Submission ID Not Found'


@mock_dynamodb
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_submit_with_reports(apigw_event):
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
            'gsi1pk': {'S': 'pending'},
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
            }
        }
    )
    ret = app.lambda_handler(apigw_event, None)
    assert ret['statusCode'] == 200
    assert 'body' in ret
    ret_body = json.loads(ret['body'])
    assert ret_body['status'] == 'submitted'
    assert 'timestamp_submitted' in ret_body
    assert 'report-1' in ret_body['selected_reports']


@mock_dynamodb
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_resolve_with_reports(apigw_event_resolve):
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
            'gsi1pk': {'S': 'pending'},
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
            }
        }
    )
    ret = app.lambda_handler(apigw_event_resolve, None)
    assert ret['statusCode'] == 204
    assert 'body' not in ret


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
