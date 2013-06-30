#!/usr/bin/env python

#######################################
### Autotrader Recon Spider
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
from fatech_production.items import Vin
from fatech_production.misc.spiderutil import *
from fatech_production.misc.spidersettings import RecheckSpiderSettings
from fatech_production.templates.recheckspider import RecheckSpider

from fatech_production.misc.dbutil import DatabaseUtil

class AutoTraderVinSpider(RecheckSpider):
    """ Vin spider class which inherites ReconSpider template """

    name = 'autotrader_vin'
    allowed_domains = ['www.autotrader.com']

    def __init__(self, **kwargs):
        """
            Assign all custom settings
        """
        
        # assign the name of the website to crawl
        self.site = 'autotrader'

        # base_url to add id to
        self.base_url = "http://m.autotrader.com/vdp.html?id="

        super(AutoTraderVinSpider, self).__init__(site=self.site, base_url=self.base_url)

    def start_requests(self):
        """
            default Scrapy method to send requests
        """

        # if spider already active
        if self.settings['active'] == 'T':
            log.msg('[OVERLAP] - at %s EST' % (datetime.now(timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")), level=log.INFO)
            # Close the spider
            raise exceptions.CloseSpider('Vin Spider already active')

        # Generate ids list for reconnoitering
        url_ids = get_ids_for_vin(self.site, self.settings['block_size'])
        
        # Send URL requests
        for id in url_ids:
            req = Request("".join((self.base_url, str(id))), dont_filter=True, callback=self.parse)
            # save url_id for calling back
            req.meta['url_id'] = id
            yield req

    def parse(self, response):
        """
            a custom method to parse html response and then throw scraped items to Scrapy's pipeline
        """

        hxs = HtmlXPathSelector(response)

        vin = Vin()

        vin['site'] = self.site
        vin['url_id'] = response.request.meta['url_id']
        try:
            vin['vin'] = hxs.select('//div[@id="vdp-main-vin"]/div[@class="value ui-block-b"]/text()').extract()[0].strip()
        except:
            pass
        return vin
        