# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import math
import re
from decimal import Decimal
from os import environ

import boto3
import simplejson as json
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS, GPSTAGS
from boto3.dynamodb.conditions import Key
from loguru import logger


def lambda_handler(event, context):
    logger.debug('Event: ' + json.dumps(event))
    for record in event['Records']:
        # Make sure we're only responding to new uploads
        if record['eventSource'] != 'aws:s3' or record['eventName'] not in \
                ['ObjectCreated:Put', 'ObjectCreated:Post',
                 'ObjectCreated:CompleteMultipartUpload']:
            logger.error('Unrecognized Event: ' + json.dumps(record))
            continue
        # Make sure it's a UUIDv4 submission id filename at the path we expect
        path_regex = r"maint-img\/(?P<submission_id>[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12})"
        path_matches = re.match(path_regex, record['s3']['object']['key'])
        if path_matches:
            submission_id = path_matches.group('submission_id')
        else:
            submission_id = None
            logger.error('Unrecognized Path: ' + json.dumps(record))
            continue
        # Rekognition supports a max image size of 15MB via S3
        if record['s3']['object']['size'] > 15728640:
            catalog_image_too_large(submission_id, record)
            continue
        process_image(submission_id, record)


def process_image(submission_id, record):
    rekognition = boto3.client('rekognition')
    logger.debug(
        f"Submitting Rekognition Request for s3://{record['s3']['bucket']['name']}/{record['s3']['object']['key']}")
    response = rekognition.detect_labels(
        Image={
            'S3Object': {
                'Bucket': record['s3']['bucket']['name'],
                'Name': record['s3']['object']['key'],
            },
        },
        MinConfidence=50
    )
    labels = {
        label['Name']: Decimal(label['Confidence']).quantize(Decimal("1.000"))
        for label in response['Labels']}
    logger.info(f"Found Labels: {labels}")
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(environ['REPORT_TABLE'])
    logger.debug(f"Retrieving Reportable Options...")
    response = table.query(
        KeyConditionExpression=Key('pk').eq('reports')
    )
    reports = response['Items']
    relevant_reports = determine_relevant_reports(reports, labels)
    coord_lat, coord_lon = image_coordinates(record['s3']['bucket']['name'],
                                             record['s3']['object']['key'],
                                             submission_id)
    if coord_lat is False or coord_lon is False:
        return
    # Shouldn't be any harm in updating ml_labels ever (as opposed to PUT), since it should
    # always be the latest/best output from Rekognition. This could even be re-run periodically
    # to improve accuracy as Rekognition improves their algorithm.
    table.update_item(
        Key={
            'pk': f"submission_{submission_id}",
            'sk': f"submission_{submission_id}"
        },
        UpdateExpression='SET ml_labels = :ml_labels, relevant_reports = :relevant_reports, coords_image = :coords_image, gsi1pk = :gsi1pk, gsi1sk = :gsi1sk',
        ExpressionAttributeValues={
            ':ml_labels': labels,
            ':relevant_reports': relevant_reports,
            ':coords_image': {
                'latitude': coord_lat,
                'longitude': coord_lon
            },
            ':gsi1pk': 'pending',
            ':gsi1sk': f"submission_{submission_id}"
        }
    )


def image_coordinates(bucket_name, object_key, submission_id):
    # Attempt to extract image coordinates from the EXIF data embedded in the image
    s3 = boto3.client('s3')
    logger.debug(f"Retrieving s3://{bucket_name}/{object_key}")
    s3.download_file(bucket_name, object_key, f"/tmp/{submission_id}")
    try:
        img = Image.open(f"/tmp/{submission_id}")
    except UnidentifiedImageError:
        return False, False
    exif_data = get_exif_data(img)
    return get_lat_lon(exif_data)


def get_exif_data(image):
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]

                exif_data[decoded] = gps_data
            else:
                exif_data[decoded] = value

    return exif_data


def get_decimal_from_dms(dms, ref):
    # Convert from Degrees/Minutes/Seconds to Decimal form
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0
    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds
    return Decimal(degrees + minutes + seconds).quantize(
        Decimal("1.000000000000000"))


def get_lat_lon(exif_data):
    if "GPSInfo" in exif_data:
        gps_info = exif_data["GPSInfo"]
        gps_latitude = gps_info.get('GPSLatitude', None)
        gps_latitude_ref = gps_info.get('GPSLatitudeRef', None)
        gps_longitude = gps_info.get('GPSLongitude', None)
        gps_longitude_ref = gps_info.get('GPSLongitudeRef', None)
        lat = get_decimal_from_dms(gps_latitude, gps_latitude_ref)
        lon = get_decimal_from_dms(gps_longitude, gps_longitude_ref)
        if math.isnan(lat):
            lat = 0
        if math.isnan(lon):
            lon = 0
        return lat, lon
    return 0, 0


def determine_relevant_reports(options, labels):
    # This simply identified relevant reports by matching the manually-created
    # report labels with the labels for the image, then adds up the confidence.
    # There is probably a more accurate and sophisticated way to rank the most
    # likely reports, but this does pretty good.
    identified_reports = {}
    for image_label, image_confidence in labels.items():
        for report in options:
            if image_label in report['labels']:
                if report['sk'] not in identified_reports:
                    identified_reports[report['sk']] = 0
                identified_reports[report['sk']] += image_confidence
    return identified_reports


def catalog_image_too_large(submission_id, record):
    logger.error('Image is too large: ' + submission_id)
    # TODO: Report this back to the user via DynamoDB


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
