#!/usr/bin/env python

#######################################
### Recon Spider Template
#######################################

# Python imoports
from __future__ import with_statement
from datetime import datetime
from pytz import timezone
from array import array

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
from fatech_production.misc.spiderutil import generate_ids
from fatech_production.misc.spidersettings import ReconSpiderSettings
from fatech_production.misc.spidersettings import MainSpiderSettings


class ReconSpider(BaseSpider):
    """ Recon spider template which requests new URLs for reconnoitering, \
        parse html response and then throw scraped cars to Scrapy's pipeline. 
    """

    name = ''
    # list of http_code to force spider handles them
    handle_httpstatus_list = [301, 401, 404, 500, 501]

    # store newest found id
    newest_startid = -1
    # default & custom settings
    settings = ""

    def __init__(self, site, base_url, recon_startid=None, **kwargs):
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
        ReconSpiderSettings(site).initialize_settings()

        # Get current spider settings for this site
        self.settings = ReconSpiderSettings(site).load_settings()

        # Override recon_startid from parameter
        if recon_startid:
            self.settings['recon_startid'] = recon_startid
            # update initial recon_startid into the database
            ReconSpiderSettings(self.site).write_startid(recon_startid)
        
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
            raise exceptions.CloseSpider('Recon Spider already active')

        # Set spider is activating
        ReconSpiderSettings(self.site).write_active('T')

        log.msg('[START_ID] - %s at %s EST' % (str(self.settings['recon_startid']), datetime.now(timezone('US/Eastern'))
                .strftime("%Y-%m-%d %H:%M:%S")), level=log.INFO)
        log.msg('[CYCLES] - %s at %s EST' % (
            str(self.settings['cycles']), datetime.now(timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")), level=log.INFO)

        # requires a new recon_startid, if not, close the spider
        if self.settings['recon_startid'] == -1:
            # Close the spider and notice to provive initial start_id
            raise exceptions.CloseSpider('Provide start_id value via start_id parameter for initilizing')

        # Generate ids list for reconnoitering
        url_ids = generate_ids(self.site)
        
        # Send URL requests
        for id in url_ids:
            req = Request("".join([self.base_url, str(id)]), dont_filter=True, callback=self.parse)
            # save url_id for calling back
            req.meta['url_id'] = id
            yield req
            
    def parse(self, response):
        """
            a custom method to parse html response and then throw scraped items to Scrapy's pipeline
        """
        # Place custom code here
        pass

    def set_newest_startid(self, setting):
        """ set newest start_id value """
        
        self.newest_startid = setting if setting > self.newest_startid else self.newest_startid

    def fireon_spider(self, spider):
        """ send curl request to fire on next spider """

        import subprocess
        command = "".join(("curl http://localhost:6800/schedule.json -d project=fatech_production -d spider=", self.site, "_", spider))
        subprocess.call(command, shell=True)     

    def spider_closed(self, spider):
        """
            Do staff when spider is closed
        """

        if spider is not self:
            return

        # Set deactive the spider
        ReconSpiderSettings(self.site).write_active('F')
        
        # Set settings if it needs to be reset
        if self.newest_startid > -1:
            # reset cycles
            ReconSpiderSettings(self.site).write_cycles(1)
            # Write a new start_id
            ReconSpiderSettings(self.site).write_startid(self.newest_startid)
        else:
            # Increase cycles value
            ReconSpiderSettings(self.site).write_cycles(self.settings['cycles'] + 1)
            
        # Determine main or recon spider to be fired on next
        if self.newest_startid > self.settings['main_startid'] + self.settings['block_size']:
            self.fireon_spider('main')
        else:
            self.fireon_spider('recon')

        # Log when spider is closed
        log.msg('[DEACTIVE SPIDER] - at %s EST' % (datetime.now(timezone('US/Eastern')).strftime(
            "%Y-%m-%d %H:%M:%S")), level=log.INFO)

    