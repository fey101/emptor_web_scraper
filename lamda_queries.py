#! /usr/bin/python3

import logging

import boto3


logging.basicConfig(filename='log', level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def get_aws_service(serviceName):
    client = boto3.client(serviceName)
    return client


def post_request_to_dynamodb(method, **kwargs):
    TABLENAME = 'websites'
    dynamodb_client = get_aws_service('dynamodb')
    resp = getattr(dynamodb_client, method)(TableName=TABLENAME, **kwargs)
    return resp

def query_dynamo_db_for_record_via_id(event, context):
    uid = event['uid']
    record = post_request_to_dynamodb(
        'query',
        KeyConditionExpression='#uid = :a',
        ExpressionAttributeNames={'#uid': 'uuid'},
        ExpressionAttributeValues={':a': {'S': uid}})
    return record['Items'][0]
