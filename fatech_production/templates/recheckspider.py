#!/usr/bin/env python

#######################################
### Recheck Spider Template
#######################################

# Python imoports
from __future__ import with_statement
import re
import sys
import time
from datetime import datetime
from pytz import timezone

# Scrapy imports
from scrapy import log
from scrapy import exceptions
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request

# Custom imports
from fatech_production.items import Car
from fatech_production.items import Link
from fatech_production.misc.dbutil import *
from fatech_production.misc.spidersettings import RecheckSpiderSettings


class RecheckSpider(BaseSpider):
    """ recheck spider template which requests rechecking URLs, parse html response and then throw scraped cars to Scrapy's pipeline. """

    name = ''
    # list of http_code to force spider handles them
    handle_httpstatus_list = [301, 401, 404, 500, 501] 
    
    # default & custom settings
    settings = ""

    def __init__(self, site, base_url, **kwargs):
        """
            Assign all custom settings
        """

        # name of the target website
        self.site = site
        # base url to add id to
        self.base_url = base_url

        # Connect to Scrapy Signal
        dispatcher.connect(self.spider_opened, signals.spider_opened)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        # Make sure the default settings is initialized
        RecheckSpiderSettings(site).initialize_settings()
        
        # Get current spider settings for this site
        self.settings = RecheckSpiderSettings(site).load_settings()

    def spider_opened(self, spider):
        """
            Do staff when spider is opened
        """
        
        if spider is not self:
            return

        # Log when spider is opened
        log.msg('[ACTIVE SPIDER] - at %s EST' % (datetime.now(timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")
                                                 ), level=log.INFO)
                
    def start_requests(self):
        """
            default Scrapy method to send requests
        """
        
        # if spider already active
        if self.settings['active'] == 'T':
            log.msg('[OVERLAP] - at %s EST' % (datetime.now(timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")), level=log.INFO)
            # Close the spider
            raise exceptions.CloseSpider('Recheck Spider already active')

        # if any available urls
        if len(self.settings['url_ids']) == 0:
            log.msg('[RECHECK_IS_EMPTY] - at %s EST' % (datetime.now(timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")), level=log.INFO)
            # Close the spider
            raise exceptions.CloseSpider('Recheck URLs is empty')             
        
        # Set spider is activating
        RecheckSpiderSettings(self.site).write_active('T')

        log.msg('[URL_QUANTITY] - %s at %s EST' % (len(self.settings['url_ids']), datetime.now(timezone('US/Eastern'))
                .strftime("%Y-%m-%d %H:%M:%S")), level=log.INFO)

        for id in self.settings['url_ids']:
            req = Request("".join((self.base_url, str(id))), dont_filter=True, callback=self.parse)
            req.meta['url_id'] = id
            yield req

    def parse(self, response):
        """
            a custom method to parse html response and then throw scraped items to Scrapy's pipeline
        """
        # Place custom code here
        pass

    def spider_closed(self, spider):
        """
            Do staff spider is closed
        """

        if spider is not self:
            return

        # Set deactive the spider
        RecheckSpiderSettings(self.site).write_active('F')

        log.msg('[DEACTIVE SPIDER] - at %s EST' % (datetime.now(timezone('US/Eastern')).strftime(
            "%Y-%m-%d %H:%M:%S")), level=log.INFO)
    