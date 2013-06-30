#!/usr/bin/env python

#######################################
### Carlocate Finalcheck Spider
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
from fatech_production.templates.finalcheckspider import FinalcheckSpider

class CarlocateFinalcheckSpider(FinalcheckSpider):
    """ Carlocate finalcheck spider which inherites FinalcheckSpider template """

    name = 'carlocate_finalcheck'
    allowed_domains = ['www.carlocate.com']

    def __init__(self, **kwargs):
        """
            Assign all custom settings
        """
        
        # assign the name of the website to crawl
        self.site = 'carlocate'
        # base_url to add id to
        self.base_url = "http://www.carlocate.com/Pages/VehicleDetail.aspx?id="

        super(CarlocateFinalcheckSpider, self).__init__(site=self.site, base_url=self.base_url)
        
    def parse(self, response):
        """
            a custom method to parse html response and then throw scraped items to Scrapy's pipeline
        """
        # Reuse the method of Carlocate Recon Spider
        from carlocate_recon import CarlocateReconSpider
        return CarlocateReconSpider().parse(response)
    