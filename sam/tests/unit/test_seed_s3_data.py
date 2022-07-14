import os
from unittest import mock

import boto3
import pytest
from moto import mock_s3

from sam.seed_s3_data import app


@pytest.fixture()
def cloudformation_event():
    return {
        "RequestType": "Create",
        "ServiceToken": "REDACTED",
        "ResponseURL": "REDACTED",
        "StackId": "REDACTED",
        "RequestId": "REDACTED",
        "LogicalResourceId": "SeedS3Data",
        "ResourceType": "Custom::SeedS3Data",
        "ResourceProperties": {
            "ServiceToken": "REDACTED",
            "StaticWebsiteBucket": "test-bucket-static-website",
            "ApiBaseURL": "TEST_API_BASE_URL",
            "UniqueSuffix": "TEST_UNIQUE_SUFFIX",
            "UploadedImagesBucket": "test-bucket-uploaded-images",
            "IdentityPoolId": "TEST_IDENTITY_POOL"
        }
    }


@mock_s3
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_seed_data(cloudformation_event):
    boto3.setup_default_session()
    s3 = boto3.client('s3')
    website_bucket = s3.create_bucket(
        Bucket='test-bucket-static-website',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )
    images_bucket = s3.create_bucket(
        Bucket='test-bucket-uploaded-images',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )
    os.chdir('seed_s3_data')
    ret = app.seed_data(cloudformation_event, None)

    with open('/tmp/website/website/js/config.js', 'r') as file:
        config_data = file.read()
        assert 'TEST_API_BASE_URL' in config_data
        assert 'TEST_UNIQUE_SUFFIX' in config_data
        assert 'TEST_IDENTITY_POOL' in config_data
    response = s3.list_objects_v2(
        Bucket='test-bucket-static-website'
    )
    assert response['KeyCount'] > 0


@mock_s3
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_seed_data_with_existing_data(cloudformation_event):
    boto3.setup_default_session()
    s3 = boto3.client('s3')
    website_bucket = s3.create_bucket(
        Bucket='test-bucket-static-website',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )
    images_bucket = s3.create_bucket(
        Bucket='test-bucket-uploaded-images',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )
    s3.put_object(
        Bucket='test-bucket-static-website',
        Key='test-data-object',
        Body=b'test-data'
    )
    ret = app.seed_data(cloudformation_event, None)
    response = s3.list_objects_v2(
        Bucket='test-bucket-static-website'
    )
    assert response['KeyCount'] == 1


@mock_s3
@mock.patch.dict(os.environ, {'REPORT_TABLE': 'TEST_REPORT_TABLE'})
@mock.patch.dict(os.environ, {'ALLOW_ORIGIN_HEADER_VALUE': 'TEST_HEADER_VALUE'})
def test_delete_data_with_existing_data(cloudformation_event):
    boto3.setup_default_session()
    s3 = boto3.client('s3')
    website_bucket = s3.create_bucket(
        Bucket='test-bucket-static-website',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )
    images_bucket = s3.create_bucket(
        Bucket='test-bucket-uploaded-images',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )
    s3.put_object(
        Bucket='test-bucket-static-website',
        Key='test-data-object',
        Body=b'test-data'
    )
    ret = app.delete_data(cloudformation_event, None)
    response = s3.list_objects_v2(
        Bucket='test-bucket-static-website'
    )
    assert response['KeyCount'] == 0
