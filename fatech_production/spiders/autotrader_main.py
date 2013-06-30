#!/usr/bin/env python

#######################################
### Autotrader Main Spider
#######################################

# Python imoports
from __future__ import with_statement
import re
import sys
import time
from datetime import datetime
from pytz import timezone
from array import array

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
from fatech_production.misc.spiderutil import *
from fatech_production.templates.mainspider import MainSpider

class AutoTraderMainSpider(MainSpider):
    """ Autotrader main spider which inherites MainSpider template """

    name = 'autotrader_main'
    allowed_domains = ['www.autotrader.com']

    def __init__(self, **kwargs):
        """
            Assign all custom settings
        """
        
        # assign the name of the website to crawl
        self.site = 'autotrader'

        # base_url to add id to
        self.base_url = "http://www.autotrader.com/cars-for-sale/popup/vehiclehighlights.xhtml?listingId="

        super(AutoTraderMainSpider, self).__init__(site=self.site, base_url=self.base_url)

        #self.driver = webdriver.PhantomJS()
        #self.driver = webdriver.Firefox()

    def parse(self, response):
        """
            a custom method to parse html response and then throw scraped items to Scrapy's pipeline
        """
        # Reuse the method of Carlocate Recon Spider
        from autotrader_recon import AutoTraderReconSpider
        return AutoTraderReconSpider().parse(response)
    