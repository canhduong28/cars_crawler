#!/usr/bin/env python

#######################################
### Carlocate Recon Spider
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
from fatech_production.templates.reconspider import ReconSpider

class CarlocateReconSpider(ReconSpider):
    """ Recon spider class which inherites ReconSpider template """

    name = 'carlocate_recon'
    allowed_domains = ['www.carlocate.com']

    def __init__(self, recon_startid=None, **kwargs):
        """
            Assign all custom settings
        """
        
        # assign the name of the website to crawl
        self.site = 'carlocate'

        # base_url to add id to
        self.base_url = "http://www.carlocate.com/Pages/VehicleDetail.aspx?id="

        super(CarlocateReconSpider, self).__init__(site=self.site, base_url=self.base_url, recon_startid=recon_startid)

    def parse(self, response):
        """
            a custom method to parse html response and then throw scraped items to Scrapy's pipeline
        """
        
        items = []

        if response.url == 'http://www.carlocate.com/SearchCars.aspx':
            ### Found no car
            link = Link()
            link['url_id'] = response.request.meta['url_id']
            link['url'] = 'http://www.carlocate.com/Pages/VehicleDetail.aspx?id=' + str(response.request.meta['url_id'])
            link['status'] = 'E'
            link['site'] = self.site

            items.append(link)
        else:
            ### A new car is found
            hxs = HtmlXPathSelector(response)
            
            car = Car()

            car['site'] = self.site
            car['source_url'] = response.url
            car['url_id'] = response.request.meta['url_id']

            ### Extracting description, and then call extract_YMMT from spiderutil to get year, make, model, trim
            car['description'] = hxs.select('//div[@class="detHeadInnerL blue"]/h1/text()').extract()[0].strip()
            result = extract_YMMT(car['description'])
            if result != - 1:
                car['year'] = result['year']
                car['make'] = result['make']
                car['model'] = result['model']
                car['trim'] = result['trim']
            else:
                # Drop the item when unable to extract year, make, model, trim
                log.msg('[WARNING] Unable to extract YearMakeModelTrim!', level=log.INFO)
                return

            ### Extracing price ###
            try:
                price = hxs.select('//div[@class="detHeadInnerR"]/text()').extract()[0].strip()
                car['price'] = extract_price(price)
            except:
                car['price'] = "-1"
                pass

            ### key_list holds list of fields,
            ### text_list holds values of corresponding fields
            ### Go though each field to assign it's value
            key_list = hxs.select('//ul[@class="detDescripInfoL"]/li/span/text()').extract()
            text_list = hxs.select('//ul[@class="detDescripInfoL"]/li/text()').extract()

            for i in xrange(len(key_list)):
                key = key_list[i]
                key = re.sub(r' #', '_id', key)
                key = re.sub(r' ', '_', key)
                key = re.sub(r':', '', key).strip().lower()
                text = text_list[i].strip()
                if key.encode('utf-8') == 'color':
                    car['exterior_color'] = text
                else:
                    car[key.encode('utf-8')] = text

            ### key_list holds list of fields,
            ### text_list holds values of corresponding fields
            ### Go though each field to assign it's value
            key_list = hxs.select('//ul[@class="detDescripInfoM"]/li/span/text()').extract()
            text_list = hxs.select('//ul[@class="detDescripInfoM"]/li/text()').extract()

            for i in xrange(len(key_list)):
                key = key_list[i]
                key = re.sub(r' ', '_', key)
                key = re.sub(r':', '', key).strip().lower()
                text = text_list[i].strip()
                if key.encode('utf-8') == 'mileage':
                    car['mileage'] = text.replace(',', '')
                elif key.encode('utf-8') == 'doors':
                    car['doors'] = doors_tostring(text)
                elif key.encode('utf-8') == 'drivetrain':
                    car['drive_type'] = text
                else:
                    car[key.encode('utf-8')] = text

            # Extracting dealer
            car['dealer'] = hxs.select('//div[@class="detSelInfoL"]/ul/li[1]/span/a/text()').extract()[0].strip()

            # Extracting street info
            street_info = hxs.select('//div[@class="detSelInfoL"]/ul/li[2]/text()').extract()[0]
            street_info = street_info.strip()
            street_info = extract_street(street_info)
            car['street_number'] = street_info['street_number']
            car['street_name'] = street_info['street_name']

            # Extracting city info
            city_info = hxs.select('//div[@class="detSelInfoL"]/ul/li[3]/text()').extract()[0]
            city_info = extract_CSZ(city_info)
            car['city'] = city_info['city']
            car['zip_code'] = city_info['zip_code']
            car['state'] = city_info['state']
        
            # Extracting phone number
            phone = hxs.select('//div[@class="detSelInfoL"]/ul/li[4]/span/text()').extract()
            if not phone:
                phone = hxs.select('//div[@class="detPhoneCTC"]/a/b/text()').extract()
            car['phone'] = phone[0].strip()

            # Set a new start_id
            self.set_newest_startid(int(response.request.meta['url_id']))

            items.append(car)

            link = Link()
            link['url'] = 'http://www.carlocate.com/Pages/VehicleDetail.aspx?id=' + str(response.request.meta['url_id'])
            link['url_id'] = response.request.meta['url_id']
            link['status'] = 'S'
            link['site'] = self.site
            items.append(link)

        return items
