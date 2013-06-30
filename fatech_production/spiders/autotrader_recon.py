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
from fatech_production.misc.spiderutil import *
from fatech_production.misc.spidersettings import ReconSpiderSettings
from fatech_production.templates.reconspider import ReconSpider

    
class AutoTraderReconSpider(ReconSpider):
    """ Recon spider class which inherites ReconSpider template """

    name = 'autotrader_recon'
    allowed_domains = ['www.autotrader.com']

    def __init__(self, recon_startid=None, **kwargs):
        """
            Assign all custom settings
        """
        
        # assign the name of the website to crawl
        self.site = 'autotrader'

        # base_url to add id to
        self.base_url = "http://www.autotrader.com/cars-for-sale/popup/vehiclehighlights.xhtml?listingId="

        super(AutoTraderReconSpider, self).__init__(site=self.site, base_url=self.base_url, recon_startid=recon_startid)

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
            req = Request("".join((self.base_url, str(id))), dont_filter=True, callback=self.parse)
            # save url_id for calling back
            req.meta['url_id'] = id
            yield req
            
    def parse(self, response):
        """
            a custom method to parse html response and then throw scraped items to Scrapy's pipeline
        """

        items = []

        if response.status == 200:

            hxs = HtmlXPathSelector(response)            

            car = Car()

            car['site'] = self.site
            car['source_url'] = response.url
            car['url_id'] = response.request.meta['url_id']

            try:
                ### Extracting description, and then call extract_YMMT from spiderutil to get year, make, model, trim
                car['description'] = hxs.select('//span[@class="listing-title"]/text()').extract()[0].strip()
            except:
                link = Link()
                link['url'] = self.base_url + str(response.request.meta['url_id'])
                link['url_id'] = response.request.meta['url_id']
                link['status'] = 'E'
                link['site'] = self.site
                return link

            result = extract_YMMT(car['description'])
            if result != - 1:
                car['year'] = result['year']
                car['make'] = result['make']
                car['model'] = result['model']
                car['trim'] = result['trim']
            else:
                # Drop the item when unable to extract year, make, model, trim
                log.msg('[WARNING] Unable to extract YearMakeModelTrim!', level=log.INFO)
                return []

            ### Extracing price ###
            try:
                price = hxs.select('//span[@class="primary-price"]/text()').extract()
                car['price'] = extract_price(price[0].strip())
            except:
                car['price'] = "-1"
                pass

            key_list = hxs.select('//div[@class="atcui atcui-container atcui-quinary atcui-gradient atcui-small atcui-clearfix vehicle-details "]/table/tr/td[1]/text()').extract()
            text_list = hxs.select('//div[@class="atcui atcui-container atcui-quinary atcui-gradient atcui-small atcui-clearfix vehicle-details "]/table/tr/td[2]/text()').extract()

            for i in xrange(len(key_list)):
                key = key_list[i].strip()
                text = text_list[i].strip()
                key = re.sub(r' ', '_', key).lower()
                if key.encode('utf-8') == 'doors':
                    car['doors'] = doors_tostring(text)
                elif 'stock' in key:
                    car['stock_id'] = text
                else:
                    car[key.encode('utf-8')] = text

            # Extracting dealer
            car['dealer'] = hxs.select('//span[@class="owner-name"]/text()').extract()[0].strip()

            try:
                # Extracting street info
                street_info = hxs.select('//span[@class="address1"]/text()').extract()[0]
                street_info = street_info.strip()
                street_info = extract_street(street_info)
                car['street_number'] = street_info['street_number']
                car['street_name'] = street_info['street_name']

                # Extracting city info
                city_info = hxs.select('//span[@class="cityStateZip"]/text()').extract()[0]
                city_info = extract_CSZ(city_info)
                car['city'] = city_info['city']
                car['zip_code'] = city_info['zip_code']
                car['state'] = city_info['state']
            except:
                pass
            
            # Extracting phone number
            try:
                phone = hxs.select('//div[@class="atcui atcui-container atcui-quinary atcui-gradient atcui-small atcui-clearfix dealer-information "]//div[@class="atcui-block"]/text()').extract()[0].strip()
                car['phone'] = extract_phone(phone)
            except:
                car['phone'] = None
                
            # Set a new start_id
            self.set_newest_startid(int(response.request.meta['url_id']))

            items.append(car)

            link = Link()
            link['url'] = self.base_url + str(response.request.meta['url_id'])
            link['url_id'] = response.request.meta['url_id']
            link['status'] = 'S'
            link['site'] = self.site
            items.append(link)

        else:
            link = Link()
            link['url'] = self.base_url + str(response.request.meta['url_id'])
            link['url_id'] = response.request.meta['url_id']
            link['status'] = 'E'
            link['site'] = self.site
            items.append(link)
        
        return items
