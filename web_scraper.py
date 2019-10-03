import logging

from urllib.parse import urlparse

from bs4 import BeautifulSoup

import requests


LOGGER = logging.getLogger(__name__)


def get_title(datapage):
    title = ''
    if datapage.title.string:
        title = datapage.title.string
    elif datapage.find('h1') is not None:
        title = datapage.find('h1').getText()
    return title


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
        datapage = BeautifulSoup(resp.content, 'html.parser')
        return get_title(datapage)
    else:
        LOGGER.error("Encountered error {0} with msg {1}.".format(
            resp.status_code, resp.reason))
