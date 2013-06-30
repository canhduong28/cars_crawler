#!/usr/bin/env python

#######################################
### Main Spider Template
#######################################

# Python imoports
from __future__ import with_statement
from datetime import datetime
from pytz import timezone
from array import array
import random

# Scrapy imports
from scrapy import log
from scrapy import exceptions
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.spider import BaseSpider
from scrapy.http import Request

# Custom imports
from fatech_production.items import Car
from fatech_production.items import Link
from fatech_production.misc.dbutil import *
from fatech_production.misc.spidersettings import MainSpiderSettings 


class MainSpider(BaseSpider):
    """ main spider template which requests new URLs from start_id to found_id, \
    parse html response and then throw scraped cars to Scrapy's pipeline. """

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
        MainSpiderSettings(site).initialize_settings()

        # Get current spider settings for this site
        self.settings = MainSpiderSettings(site).load_settings()
            
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
            raise exceptions.CloseSpider('Main Spider already active')

        # Set spider is activating
        MainSpiderSettings(self.site).write_active('T')

        # If new recon_start is existed
        if self.settings['recon_startid'] == -1:
            raise exceptions.CloseSpider('It requires to run Recon Spider to looking for new ids before running Main Spider.')         

        # If main_startid is existed
        if self.settings['main_startid'] == -1:
            # set a temporary start_id
            self.settings['main_startid'] = self.settings['recon_startid'] - self.settings['block_size']
        
        log.msg('[START_ID] - %s at %s EST' % (str(self.settings['main_startid']), datetime.now(timezone('US/Eastern'))
                .strftime("%Y-%m-%d %H:%M:%S")), level=log.INFO)
        log.msg('[FOUND_GAP] - %s at %s EST' % (
            str(self.settings['recon_startid'] - self.settings['main_startid']), datetime.now(timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")), level=log.INFO)

        # generate an array of url_ids
        url_ids = array('i',(xrange(self.settings['main_startid'], self.settings['main_startid'] + self.settings['block_size'])))

        # Shuffle the id list before requesting
        random.shuffle(url_ids)
        
        for id in url_ids:
            req = Request("".join([self.base_url, str(id)]), dont_filter=True, callback=self.parse)
            req.meta['url_id'] = id
            yield req
            
    def parse(self, response):
        """
            a custom method to parse html response and then throw scraped items to Scrapy's pipeline
        """
        # Place custom code here
        pass

    def fireon_spider(self, spider):
        """ send curl request to fire on next spider """

        import subprocess
        command = "".join(("curl http://localhost:6800/schedule.json -d project=fatech_production -d spider=", self.site, "_", spider))
        subprocess.call(command, shell=True)

    def spider_closed(self, spider):
        """
            Do staff spider is closed
        """

        if spider is not self:
            return

        # Write a new start_id for next run
        MainSpiderSettings(self.site).write_startid(self.settings['main_startid'] + self.settings['block_size'])
        # Set deactive the spider
        MainSpiderSettings(self.site).write_active('F')

        # Determine main or recon spider to be fired on next
        if self.settings['main_startid'] + 2*self.settings['block_size'] < self.settings['recon_startid']: 
            self.fireon_spider('main')
        else:
            self.fireon_spider('recon')

        log.msg('[DEACTIVE SPIDER] - at %s EST' % (datetime.now(timezone('US/Eastern')).strftime(
            "%Y-%m-%d %H:%M:%S")), level=log.INFO)

    

        

    