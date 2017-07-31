#!/usr/bin/env python3
"""Searching and Downloading Google Images/Image Links."""

# Import Libraries

from os.path import basename
from urllib.parse import quote
import logging
import os
import time  # Importing the time library to check the time of code execution
import shutil
try:
    from urllib2 import urlopen, Request, URLError, HTTPError
except ImportError:
    from urllib.request import urlopen, Request, URLError, HTTPError  # For 3.6.X Python

from fake_useragent import UserAgent
from send2trash import send2trash

from .sha256 import sha256_checksum


def download_page(url):
    """Downloading entire Web Document (Raw Page Content)."""
    ua = UserAgent()
    headers = {'User-Agent': ua.firefox}
    req = Request(url, headers=headers)
    response = urlopen(req)
    page = str(response.read())
    return page


def _images_get_next_item(s):
    """Finding 'Next Image' from the given raw page."""
    start_line = s.find('rg_di')
    if start_line == -1:  # If no links are found then give an error!
        end_quote = 0
        link = "no_links"
        return link, end_quote
    else:
        start_line = s.find('"class="rg_meta"')
        start_content = s.find('"ou"', start_line + 1)
        end_content = s.find(',"ow"', start_content + 1)
        content_raw = str(s[start_content + 6:end_content - 1])
        return content_raw, end_content


def _images_get_all_items(page):
    """Getting all links with the help of '_images_get_next_image'."""
    items = []
    while True:
        item, end_content = _images_get_next_item(page)
        if item == "no_links":
            break
        else:
            items.append(item)  # Append all the links in the list named 'Links'
            time.sleep(0.1)  # Timer could be used to slow down the request for image downloads
            page = page[end_content:]
    return items


def rename_basename(old_filename, new_basename):
    """rename basename."""
    dirname = os.path.dirname(old_filename)
    _, ext = os.path.splitext(os.path.os.path.basename(old_filename))
    return os.path.join(dirname, '{}{}'.format(new_basename, ext))


class Downloader:
    """downloader class."""

    def __init__(self):
        """init method."""
        self.error_count = 0
        self.dl_counter = 0
        self.skip_counter = 0
        self.ua = UserAgent()

    def run(self, item, filename, filename_format='basename', no_clobber=True):
        """run downloader.

        If filename format is not `basename`, then after URL downloaded to `filename` file,
        it will renamed based on the choosen `filename_format`.
        If filename with the new `filename_format` already exist and `no-clobber` is `True`,
        the downloaded file will be deleted and download will be counted as skipped.
        If filename with the new `filename_format` already exist and `no-clobber` is `False`,
        the downloaded file will replace existing file and download will be counted as succcess.

        Args:
            item: Url to be downloaded.
            filename: Filename of the url.
            filename_format: Filename format of the url.
        """
        try:
            req = Request(item, headers={"User-Agent": self.ua.firefox})
            with urlopen(req) as response, \
                    open(filename, 'wb') as output_file:
                data = response.read()
                output_file.write(data)

            # assume file is not exist when another filename_format is choosen
            file_already_exist = False
            new_filename = None
            if filename_format == 'sha256':
                new_basename = sha256_checksum(filename=filename)  # without extension
                new_filename = rename_basename(old_filename=filename, new_basename=new_basename)

                new_filename_exist = os.path.isfile(new_filename)
                if new_filename_exist:
                    logging.debug('Exist: {}'.format(new_filename))

                if new_filename_exist and no_clobber:
                    file_already_exist = True
                    send2trash(filename)  # remove downloaded file
                else:
                    # this will rename or move based on the condition.
                    shutil.move(filename, new_filename)
            else:
                logging.debug('Unknown filename format: {}'.format(filename_format))

            if file_already_exist:
                print('Skipped\t\t====> {}'.format(new_filename))
                self.dl_counter += 1
            else:
                print("completed\t====> {}".format(filename))
                self.dl_counter += 1

        except IOError:  # If there is any IOError
            self.error_count += 1
            print("IOError on image {}".format(filename))

        except HTTPError as e:  # If there is any HTTPError
            self.error_count += 1
            print("HTTPError {}".format(filename))

        except URLError as e:
            self.error_count += 1
            print("URLError {}".format(filename))


def get_google_image_items(query):
    quoted_query = quote(query)
    url = 'https://www.google.com/search?q=' + quoted_query + '&espv=2&biw=1366&bih=667&site=webhp&source=lnms&tbm=isch&sa=X&ei=XosDVaCXD8TasATItgE&ved=0CAcQ_AUoAg'  # NOQA
    raw_html = (download_page(url))
    return _images_get_all_items(raw_html)


def get_image_links(search_keyword, keywords, requests_delay):
    """get image links."""
    t0 = time.time()  # start the timer
    items = []
    # Download Image Links
    for i, search_keyword in enumerate(search_keywords):
        print("Item no.: {} --> Item name = {}".format(i + 1, search_keyword))
        print("Evaluating...")
        if not keywords:
            items = items + get_google_image_items(query=search_keyword)

        for j, keyword in enumerate(keywords):
            items = items + get_google_image_items(query=' '.join([search_keyword, keyword]))

            # delay is required here
            if requests_delay == 0:
                time.sleep(0.1)
            else:
                time.sleep(requests_delay)

        print("Total Image Links = {}\n".format(len(items)))

    t1 = time.time()  # stop the timer
    # Calculating the total time required to crawl,
    # find and download all the links of 60,000 images
    total_time = t1 - t0
    print("Total time taken: {} Seconds".format(int(total_time)))
    print("Starting Download...")
    return items


def main(search_keywords, keywords, download_limit, requests_delay, no_clobber,
         filename_format='basename'):
    items = get_image_links(search_keyword, keywords, requests_delay)

    # To save imges to the same directory
    # IN this saving process we are just skipping the URL if there is any error

    downloader = Downloader()
    for k, item in enumerate(items):
        if download_limit != 0 and downloader.dl_counter >= download_limit:
            break
        filename = basename(item)
        if os.path.isfile(filename) and no_clobber:
            print('Skipped\t\t====> {}'.format(filename))
            downloader.skip_counter += 1
            continue

        downloader.run(
            item=item, filename=filename, filename_format=filename_format, no_clobber=no_clobber)

        if requests_delay != 0:
            time.sleep(requests_delay)

    print("""All url(s) are downloaded
    {} ----> total Errors
    {} ----> total Skip""".format(downloader.error_count, downloader.skip_counter))

    # ----End of the main program ----#