#!/usr/bin/env python

#######################################
### Scrapy middlewares
#######################################

# Python imports
import random
import time

# Scrapy imports
from scrapy.http import Request
from scrapy.exceptions import IgnoreRequest
from scrapy.http import HtmlResponse
from selenium import webdriver
# Custom imports
from fatech_production.settings import USER_AGENT_LIST
from fatech_production.settings import MOBILE_USER_AGENT_LIST
from proxies.proxiesutil import ProxiesUtil

class RandomUserAgentMiddleware(object):
    """
        Change randomly user-agent from USER_AGENT_LIST in setttings.py
    """
    def process_request(self, request, spider):
        if 'm.autotrader' not in request.url:
            ua = random.choice(USER_AGENT_LIST)
            request.headers.setdefault('User-Agent', ua)


class ProxyMiddleware(object):
    """
        Use proxy over each request
    """
    # overwrite process request
    def process_request(self, request, spider):
        # Set the location of the proxy
        if 'autotrader' in spider.name:
            proxy = ProxiesUtil().get_proxy()
            request.meta['proxy'] = 'http://' + proxy + ':1717'
            print request.meta['proxy']

class PhantomJSDownloader(object):

    def process_request(self, request, spider):
        if 'm.autotrader' in request.url:
            ua = random.choice(MOBILE_USER_AGENT_LIST)
            driver = webdriver.PhantomJS(desired_capabilities={'javascriptEnabled': False, 'browserName': ua})
            driver.get(request.url)
            time.sleep(.1)
            try:       
                body = driver.page_source.encode('utf-8')
                driver.quit()
            except:
                body = ""
                
            return HtmlResponse(request.url, body=body)

    def process_response(self, request, response, spider):
        if response.body == "":
            raise IgnoreRequest()
        else:
            return response
            

            
