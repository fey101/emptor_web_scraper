#! /usr/bin/python3

import logging

from tempfile import NamedTemporaryFile

from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup

import requests

import boto3


LOGGER = logging.getLogger(__name__)


def post_data_to_s3(key, data_string):
    bucket = 'emptor-experiments'
    s3client = boto3.client('s3')
    with NamedTemporaryFile('wb+', suffix='.txt') as ntempfile:
        ntempfile.file.write(data_string)
        ntempfile.file.flush()
        ntempfile.file.seek(0)
        from pdb import set_trace
        set_trace()
        try:
            s3client.upload_fileobj(ntempfile.file, bucket, key)
            location = s3client.get_bucket_location(
                Bucket=bucket)['LocationConstraint']
            objecturl = f'https://{bucket}.s3-{location}.amazonaws.com/{quote(key)}'
            return objecturl
        except Exception as e:
            LOGGER.error('Failed to create specified object on s3.' +
                         ' {}'.format(e))


def post_title_to_dynamodb(key, value):
    dynamodb_client = boto3.client('dynamodb')
    try:
        item = {
            "name": {
                'S': key,
            },
            "title": {
                'S': value
            },
        }
        dynamodb_client.put_item(TableName='web_scraper', Item=item)
    except Exception as e:
        LOGGER.error('Failed to create specified object on dynamodb.' +
                     ' {}'.format(e))


def get_title(datapage):
    title = ''
    if datapage.title.string:
        title = datapage.title.string
    elif datapage.find('h1') is not None:
        title = datapage.find('h1').getText()

    return title.strip()


def scraper(user_supplied_url):
    # Validate supplied url. At the bare minimum we need a scheme and netloc.
    # urlparse also decod
    parsed_url = urlparse(user_supplied_url)
    is_url = all([parsed_url.scheme, parsed_url.netloc])
    if not is_url:
        LOGGER.error("The supplied url must contain a scheme and netloc")
        return

    # else
    url = parsed_url.geturl()
    baseheaders = requests.utils.default_headers()
    resp = requests.get(url, headers=baseheaders)
    if resp.status_code == 200:
        safe_url = quote(url)
        s3_objurl = post_data_to_s3(safe_url, resp.content)
        datapage = BeautifulSoup(resp.content, 'html.parser')
        pagetitle = get_title(datapage)
        post_title_to_dynamodb(safe_url, pagetitle)
        return s3_objurl, pagetitle
    else:
        LOGGER.error("Encountered error {0} with msg {1}.".format(
            resp.status_code, resp.reason))
