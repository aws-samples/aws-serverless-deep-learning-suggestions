import os
import shutil
from decimal import *
from unittest import mock

import boto3
import botocore.session
import pytest
from botocore.stub import Stubber
from moto import mock_dynamodb, mock_s3

from sam.process_upload import app


@pytest.fixture()
def s3_event():
    return {
        'Records': [
            {
                'eventSource': 'aws:s3',
                'awsRegion': 'us-west-2',
                'eventName': 'ObjectCreated:Put',
                's3': {
                    'bucket': {
                        'name': 'test-bucket-uploaded-images',
                        'arn': 'arn:aws:s3:::test-bucket-uploaded-images'
                    },
                    'object': {
                        'key': 'maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81',
                        'size': 7950419
                    }
                }
            }
        ]
    }


@pytest.fixture()
def s3_event_too_big():
    return {
        'Records': [
            {
                'eventSource': 'aws:s3',
                'awsRegion': 'us-west-2',
                'eventName': 'ObjectCreated:Put',
                's3': {
                    'bucket': {
                        'name': 'test-bucket-uploaded-images',
                        'arn': 'arn:aws:s3:::test-bucket-uploaded-images'
                    },
                    'object': {
                        'key': 'maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81',
                        'size': 16777216
                    }
                }
            }
        ]
    }


@pytest.fixture()
def s3_event_wrong_event():
    return {
        'Records': [
            {
                'eventSource': 'aws:s3',
                'awsRegion': 'us-west-2',
                'eventName': 's3:ObjectRemoved:Delete',
                's3': {
                    'bucket': {
                        'name': 'test-bucket-uploaded-images',
                        'arn': 'arn:aws:s3:::test-bucket-uploaded-images'
                    },
                    'object': {
                        'key': 'maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81',
                        'size': 7950419213
                    }
                }
            }
        ]
    }


@pytest.fixture()
def s3_event_bad_id():
    return {
        'Records': [
            {
                'eventSource': 'aws:s3',
                'awsRegion': 'us-west-2',
                'eventName': 'ObjectCreated:Put',
                's3': {
                    'bucket': {
                        'name': 'test-bucket-uploaded-images',
                        'arn': 'arn:aws:s3:::test-bucket-uploaded-images'
                    },
                    'object': {
                        'key': 'maint-img/97cc0239',
                        'size': 7950419213
                    }
                }
            }
        ]
    }


def boto3_client_side_effect(*args, **kwargs):
    if args[0] == 'rekognition':
        rekognition = botocore.session.get_session().create_client(
            'rekognition')
        stubber = Stubber(rekognition)
        stubber.add_response(
            'detect_labels',
            {
                'Labels': [
                    {'Name': 'Fire Hydrant', 'Confidence': Decimal(95.725)},
                    {'Name': 'Hydrant', 'Confidence': Decimal(95.725)},
                    {'Name': 'Tarmac', 'Confidence': Decimal(77.266)},
                    {'Name': 'Asphalt', 'Confidence': Decimal(77.266)},
                    {'Name': 'Road', 'Confidence': Decimal(76.261)},
                    {'Name': 'Gravel', 'Confidence': Decimal(57.343)},
                    {'Name': 'Dirt Road', 'Confidence': Decimal(57.343)},
                    {'Name': 'Ground', 'Confidence': Decimal(55.491)}
                ]
            },
            {'Image': botocore.stub.ANY, 'MinConfidence': botocore.stub.ANY}
        )
        stubber.activate()
        return rekognition
    else:
        return boto3.client

def boto3_client_side_effect_rek_invalid_image(*args, **kwargs):
    if args[0] == 'rekognition':
        rekognition = botocore.session.get_session().create_client(
            'rekognition')
        stubber = Stubber(rekognition)
        stubber.add_client_error(
            method='detect_labels',
            service_error_code='InvalidImageFormatException'
        )
        stubber.activate()
        return rekognition
    else:
        return boto3.client


@mock_dynamodb
@mock_s3
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler(s3_event):
    s3 = boto3.client('s3')
    bucket = s3.create_bucket(
        Bucket='test-bucket-uploaded-images',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )
    with open('tests/assets/example_upload.jpg', 'rb') as data:
        s3.upload_fileobj(data, 'test-bucket-uploaded-images',
                          'maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81')
        # Because the mocked s3.download_file doesn't actually do anything.
        shutil.copy('tests/assets/example_upload.jpg',
                    '/tmp/97cc0239-34fc-49d1-b87a-eb226ecc0e81')
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
    with mock.patch('boto3.client',
                    mock.MagicMock(side_effect=boto3_client_side_effect)):
        app.lambda_handler(s3_event, None)
    response = client.get_item(
        TableName=os.environ['REPORT_TABLE'],
        Key={
            'pk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'},
            'sk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'}
        },
    )
    assert response['Item']['coords_image']['M']['latitude']['N'].startswith(
        '33.719')
    assert response['Item']['coords_image']['M']['longitude']['N'].startswith(
        '-112.175')
    assert response['Item']['gsi1pk']['S'] == 'pending'
    assert response['Item']['relevant_reports']['M']['report-1'][
        'N'].startswith('191.45')
    assert 'Fire Hydrant' in response['Item']['ml_labels']['M']


@mock_dynamodb
@mock_s3
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_image_too_big(s3_event_too_big):
    s3 = boto3.client('s3')
    bucket = s3.create_bucket(
        Bucket='test-bucket-uploaded-images',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )
    with open('tests/assets/example_upload_too_big.jpg', 'rb') as data:
        s3.upload_fileobj(data, 'test-bucket-uploaded-images',
                          'maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81')
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
    app.lambda_handler(s3_event_too_big, None)
    response = client.get_item(
        TableName=os.environ['REPORT_TABLE'],
        Key={
            'pk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'},
            'sk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'}
        },
    )
    assert 'Item' not in response
    response = s3.list_objects_v2(
        Bucket='test-bucket-uploaded-images',
        Prefix='maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81',
    )
    # No S3 Object (it was deleted)
    assert 'Contents' not in response


@mock_dynamodb
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_wrong_s3_event(s3_event_wrong_event):
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
    app.lambda_handler(s3_event_wrong_event, None)
    response = client.get_item(
        TableName=os.environ['REPORT_TABLE'],
        Key={
            'pk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'},
            'sk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'}
        },
    )
    assert 'Item' not in response



@mock_dynamodb
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_bad_id(s3_event_bad_id):
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
    app.lambda_handler(s3_event_bad_id, None)
    response = client.get_item(
        TableName=os.environ['REPORT_TABLE'],
        Key={
            'pk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'},
            'sk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'}
        },
    )
    assert 'Item' not in response


@mock_dynamodb
@mock_s3
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_photo_no_gps(s3_event):
    s3 = boto3.client('s3')
    bucket = s3.create_bucket(
        Bucket='test-bucket-uploaded-images',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )
    with open('tests/assets/example_upload_no_gps.jpg', 'rb') as data:
        s3.upload_fileobj(data, 'test-bucket-uploaded-images',
                          'maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81')
        # Because the mocked s3.download_file doesn't actually do anything.
        shutil.copy('tests/assets/example_upload_no_gps.jpg',
                    '/tmp/97cc0239-34fc-49d1-b87a-eb226ecc0e81')
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
    with mock.patch('boto3.client',
                    mock.MagicMock(side_effect=boto3_client_side_effect)):
        app.lambda_handler(s3_event, None)
    response = client.get_item(
        TableName=os.environ['REPORT_TABLE'],
        Key={
            'pk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'},
            'sk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'}
        },
    )
    assert response['Item']['coords_image']['M']['latitude']['N'] == '0'
    assert response['Item']['coords_image']['M']['longitude']['N'] == '0'
    assert response['Item']['gsi1pk']['S'] == 'pending'
    assert 'Fire Hydrant' in response['Item']['ml_labels']['M']


@mock_dynamodb
@mock_s3
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_not_a_photo(s3_event):
    with mock.patch('boto3.client',
                    mock.MagicMock(side_effect=boto3_client_side_effect_rek_invalid_image)):
        s3 = boto3.client('s3')
        bucket = s3.create_bucket(
            Bucket='test-bucket-uploaded-images',
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        with open('tests/assets/example_not_a_photo.jpg', 'rb') as data:
            s3.upload_fileobj(data, 'test-bucket-uploaded-images',
                              'maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81')
            # Because the mocked s3.download_file doesn't actually do anything.
            shutil.copy('tests/assets/example_not_a_photo.jpg',
                        '/tmp/97cc0239-34fc-49d1-b87a-eb226ecc0e81')
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
        app.lambda_handler(s3_event, None)
        response = client.get_item(
            TableName=os.environ['REPORT_TABLE'],
            Key={
                'pk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'},
                'sk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'}
            },
        )
        assert 'Item' not in response
        response = s3.list_objects_v2(
            Bucket='test-bucket-uploaded-images',
            Prefix='maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81',
        )
        # No S3 Object (it was deleted)
        assert 'Contents' not in response
        #assert response['Item']['coords_image']['M']['latitude']['N'] == '0'
        #assert response['Item']['coords_image']['M']['longitude']['N'] == '0'
        #assert response['Item']['gsi1pk']['S'] == 'pending'


@mock_dynamodb
@mock_s3
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_lambda_handler_empty_file(s3_event):
    with mock.patch('boto3.client',
                    mock.MagicMock(side_effect=boto3_client_side_effect_rek_invalid_image)):
        s3 = boto3.client('s3')
        bucket = s3.create_bucket(
            Bucket='test-bucket-uploaded-images',
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        with open('tests/assets/example_empty_file.jpg', 'rb') as data:
            s3.upload_fileobj(data, 'test-bucket-uploaded-images',
                              'maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81')
            # Because the mocked s3.download_file doesn't actually do anything.
            shutil.copy('tests/assets/example_empty_file.jpg',
                        '/tmp/97cc0239-34fc-49d1-b87a-eb226ecc0e81')
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
        with mock.patch('boto3.client',
                        mock.MagicMock(side_effect=boto3_client_side_effect_rek_invalid_image)):
            app.lambda_handler(s3_event, None)
        response = client.get_item(
            TableName=os.environ['REPORT_TABLE'],
            Key={
                'pk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'},
                'sk': {'S': 'submission_97cc0239-34fc-49d1-b87a-eb226ecc0e81'}
            },
        )
        assert 'Item' not in response
        response = s3.list_objects_v2(
            Bucket='test-bucket-uploaded-images',
            Prefix='maint-img/97cc0239-34fc-49d1-b87a-eb226ecc0e81',
        )
        # No S3 Object (it was deleted)
        assert 'Contents' not in response


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
