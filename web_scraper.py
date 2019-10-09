#! /usr/bin/python3

import asyncio

import logging

import uuid

from tempfile import NamedTemporaryFile

from urllib.parse import quote, unquote, urlparse

from bs4 import BeautifulSoup

import requests

import boto3


logging.basicConfig(filename='log', level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def get_aws_service(serviceName):
    client = boto3.client(serviceName)
    return client


def get_title(datapage):
    title = ''
    if datapage.title.string:
        title = datapage.title.string
    elif datapage.find('h1') is not None:
        title = datapage.find('h1').getText()

    return title.strip()


def valid_url(user_supplied_url):
    parsed_url = urlparse(user_supplied_url)
    is_valid = all([parsed_url.scheme, parsed_url.netloc])
    if not is_valid:
        LOGGER.error('The supplied url must contain a scheme and netloc')
        return
    clean_url = parsed_url.geturl()
    return clean_url


async def post_data_to_s3(key, data_stream):
    key = key.rstrip('/')
    bucket = 'emptor-experiments'
    s3client = get_aws_service('s3')
    with NamedTemporaryFile('rb+', suffix='.txt') as ntempfile:
        ntempfile.file.write(data_stream)
        ntempfile.file.flush()
        ntempfile.file.seek(0)
        try:
            s3client.upload_fileobj(ntempfile.file, bucket, key)
            location = s3client.get_bucket_location(
                Bucket=bucket)['LocationConstraint']
            objecturl = 'https://{0}.s3-{1}.amazonaws.com/{2}'.format(
                bucket, location, quote(key))
            return objecturl
        except Exception as e:
            LOGGER.error('Failed to create specified object on s3.' +
                         ' {}'.format(e))


def post_request_to_dynamodb(method, **kwargs):
    TABLENAME = 'websites'
    dynamodb_client = get_aws_service('dynamodb')
    resp = getattr(dynamodb_client, method)(TableName=TABLENAME, **kwargs)
    return resp


def process_website(event, context):
    user_supplied_url = event['user_supplied_url']
    url = valid_url(user_supplied_url)
    if not url:
        raise ValueError(
            'Invalid url. The supplied url must contain a scheme and netloc')

    id_string = str(uuid.uuid4())
    try:
        item = {
            'uuid': {
                'S': id_string,
            },
            'url': {
                'S': url
            },
            'state': {
                'S': 'PENDING'
            }
        }
        post_request_to_dynamodb('put_item', Item=item)
        # invoke scraper fn asynchronously
        asyncio.run(scraper(id_string), debug=True)
        return id_string
    except Exception as e:
        LOGGER.error('Failed to process request on dynamodb.' +
                     ' {}'.format(e))


async def scraper(itemId):
    key = {
        'uuid': {
            'S': itemId
        }
    }
    record = post_request_to_dynamodb('get_item', Key=key)
    url = record['Item']["url"]['S']
    LOGGER.info('Processing {}'.format(url))
    baseheaders = requests.utils.default_headers()
    user_agent = 'Mozilla/5.0 (X11; Ubuntu; ' \
        'Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
    baseheaders.update({'User-Agent': user_agent})
    resp = requests.get(url, headers=baseheaders)
    if resp.status_code == 200:
        url_string = quote(url)
        s3_objurl = await post_data_to_s3(url_string, resp.content)
        datapage = BeautifulSoup(resp.content, 'html.parser')
        pagetitle = get_title(datapage)
        update_data = {
            'state': {
                'Value': {
                    'S': 'PROCESSED'
                },
                'Action': 'PUT'
            },
            's3url': {
                'Value': {
                    'S': s3_objurl
                },
                'Action': 'PUT'
            },
        }
        if pagetitle:
            update_data.update(title={
                'Value': {'S': pagetitle},
                'Action': 'PUT'}
            )
        post_request_to_dynamodb(
            'update_item',
            Key=key,
            AttributeUpdates=update_data,
            ReturnValues='ALL_NEW'
        )
        return s3_objurl, pagetitle
    else:
        LOGGER.error('Encountered error {0} with msg {1}.'.format(
            resp.status_code, resp.reason))


def query_dynamo_db_for_record_via_id(uid):
    record = post_request_to_dynamodb(
        'query',
        KeyConditionExpression='#uid = :a',
        ExpressionAttributeNames={'#uid': 'uuid'},
        ExpressionAttributeValues={':a': {'S': uid}})
    return record['Items'][0]
