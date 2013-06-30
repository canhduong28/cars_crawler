#!/usr/bin/env python

#######################################
### Scrapy pipelines
#######################################

# Scrapy imports
from scrapy import log
from scrapy.exceptions import DropItem

# CarSpider imports
from fatech_production.settings import *
from fatech_production.items import Car
from fatech_production.items import Link
from fatech_production.items import Vin

# Python imports
from twisted.enterprise import adbapi
import MySQLdb.cursors
import MySQLdb as mdb
from datetime import datetime
from pytz import timezone
import urllib
import re

class DuplicatesPipeline(object):
    """
        DuplicatesPipeline to avoid duplicating scraped items.
        Saving all IDs have seen, and then use them to check if an incoming item is scraped.
    """

    def __init__(self):
        self.ids_seen = set()

    def process_item(self, item, spider):

        if isinstance(item, Car) and item['url_id'] in self.ids_seen:
            raise DropItem('[DUPLICATED] - %s' % str(item['url_id']))
        else:
            self.ids_seen.add(item['url_id'])
            return item
            


class MySQLPipeline(object):
    """ Pipeline to sanitize items and also handle mysql transactions """

    def __init__(self):
        """ initialize a MySQL connection object """

        self.dbpool = adbapi.ConnectionPool('MySQLdb',
                                            host=DATABASE_HOST,
                                            port=DATABASE_PORT,
                                            db=DATABASE_NAME,
                                            user=DATABASE_USER,
                                            passwd=DATABASE_PASSWORD,
                                            cursorclass=MySQLdb.cursors.DictCursor,
                                            charset='utf8',
                                            use_unicode=True
                                            )

    def sanitized(self, item):
        """ Get sanitized some fields of Cars """

        item['source_url'] = urllib.quote_plus(item.get('source_url'))
        item['dealer'] = re.sub('&', '%26', item.get('dealer', ""))
        item['description'] = re.sub('&', '%26', item.get('description', ""))
        item['trim'] = re.sub('&', '%26', item.get('trim', ""))
        item['make'] = re.sub('&', '%26', item.get('make', ""))
        item['model'] = re.sub('&', '%26', item.get('model', ""))
        item['price'] = re.sub(r',', '', item.get('price', "-1"))
        item['mileage'] = re.sub(r',', '', item.get('mileage', "-1"))
        return item

    def process_item(self, item, spider):
        """ default pipeline's method to process scraped items """

        if isinstance(item, Link):
            query = self.dbpool.runInteraction(self.process_url, item)
            query.addErrback(self.handle_error)
            return item
        elif isinstance(item, Car):
            item = self.sanitized(item)
            item['found_by'] = spider.name
            query = self.dbpool.runInteraction(self.process_car, item)
            query.addErrback(self.handle_error)
            return item
        elif isinstance(item, Vin):
            query = self.dbpool.runInteraction(self.process_vin, item)
            query.addErrback(self.handle_error)
            return item

    def process_url(self, cursor, item):
        """ insert & update URLs into the database """

        # check if URL's ID is existed
        sql = "".join(("select id from ", item.get('site'), "_urls where id = %s limit 1;"))
        parameters = (item.get('url_id'))
        cursor.execute(sql, parameters)
        result = cursor.fetchone()
        if not result:
            # insert a new URL 
            sql = "".join(("insert into ", item.get('site'), "_urls (id, url, status) values (%s, %s, %s);"))
            parameters = (item.get('url_id'), item.get('url'), item.get('status'))
            cursor.execute(sql, parameters)
        else:
            # check if URL needs to be updated
            if item.get('status') == 'S':
                sql = "".join(("update ", item.get('site'), "_urls set status = 'S' where id = %s limit 1;"))
                parameters = (item.get('url_id'))
                cursor.execute(sql, parameters)

        if item['status'] == 'S':
            log.msg("[SUCCESS] %s at %s EST" % (item['url_id'], datetime.now(timezone('US/Eastern')).strftime(
                "%Y-%m-%d %H:%M:%S")), level=log.INFO)
        else:
            log.msg("[ERROR] %s at %s EST" % (item['url_id'], datetime.now(timezone('US/Eastern')).strftime(
                "%Y-%m-%d %H:%M:%S")), level=log.INFO)

    def process_car(self, cursor, item):
        """ insert & update Cars """

        def process_make(cursor, make):
            """ check if the make & model exist in the _variations, if they do not, inserting it into _hold to manually process later """

            # make
            make = urllib.unquote_plus(make)
            sql = "select id from master_makes_variations use index(idx_make) where make = %s;"
            parameters = (make)
            cursor.execute(sql, parameters)
            result = cursor.fetchone()
            make_id = None
            if not result:
                sql = "select id from master_makes_hold use index (idx_make) where make = %s;"
                parameters = (make)
                cursor.execute(sql, parameters)
                result = cursor.fetchone()
                if not result:
                    sql = "insert into master_makes_hold(make) values (%s);"
                    parameters = (make)
                    cursor.execute(sql, parameters)
                    cursor.execute('commit;')
                    log.msg('[UNFOUND] make - %s' % make, level=log.INFO)
                    return cursor.lastrowid
                else:
                    return None
            else:
                log.msg('[FOUND] make - %s' % make, level=log.INFO)
                return result['id']

        def process_model(cursor, model, make_id):
            """ check if the model exists in the _variations, if it does not, inserting it into _hold to manually process later """            

            model = urllib.unquote_plus(model)

            sql = "select id from master_models_variations use index (idx_model) where model = %s;"
            parameters = (model)
            cursor.execute(sql, parameters)
            result = cursor.fetchone()
            if not result:
                sql = "select id from master_models_hold use index (idx_model) where model = %s;"
                parameters = (model)
                cursor.execute(sql, parameters)
                result = cursor.fetchone()
                if not result:
                    sql = "insert into master_models_hold(model, fk_make) values (%s, %s);"
                    parameters = (model, str(make_id))
                    cursor.execute(sql, parameters)
                    cursor.execute('commit;')
                    log.msg('[UNFOUND] model - %s' % model, level=log.INFO)
            else:
                log.msg('[FOUND] model - %s' % model, level=log.INFO)

        # Check if Car's Vin is existed
        sql = "select RowNum from master_vin use index(Idx_VIN) where VIN = %s limit 1;"
        if item.get('vin') is not None:
            parameters = (item.get('vin'))
        else:
            parameters = ("")
        cursor.execute(sql, parameters)
        result = cursor.fetchone()
        if result:
            # Vin is duplicated, then set target table is _history
            target_table = "_history"
        else:
            # Vin is new, then set target table is _cars
            target_table = "_cars"

        # check if Car's ID is existed
        sql = "".join(("select id from ", item.get('site'), "_cars where id = %s limit 1;"))
        parameters = (item.get('url_id'))
        cursor.execute(sql, parameters)
        result = cursor.fetchone()
        if not result:
            
            # joining site and target_table to choose correct data table and then insert a new Car
            sql = "".join(("insert into ", item.get('site'), target_table ,"(id, description, `year`, make, trim, model, price, bodystyle,\
                exterior_color, interior_color, `engine`, stock_id, vin, mileage, transmission, drive_type, doors, fuel, cab, stereo, dealer, street_number, \
                street_name, city, state, zip_code, phone, source_url, found_by) \
                values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"))
            parameters = (
                item.get('url_id'), item.get('description'), item.get('year'), item.get('make'), item.get('trim'),
                item.get('model'), item.get('price'), item.get('body_style'), item.get('exterior_color'), item.get('interior_color'),
                item.get('engine'), item.get('stock_id'), item.get('vin'), item.get('mileage'), item.get('transmission'), item.get('drive_type'),
                item.get('doors'), item.get('fuel_type'), item.get('cab_type'), item.get('stereo'), item.get('dealer'), item.get('street_number'), 
                item.get('street_name'), item.get('city'), item.get('state'), item.get('zip_code'), item.get('phone'), item.get('source_url'),
                item.get('found_by')

            )
            cursor.execute(sql, parameters)
            log.msg('[ADDED] %s at %s EST' % (item['description'], datetime.now(timezone('US/Eastern'))
                    .strftime("%Y-%m-%d %H:%M:%S")), level=log.INFO)

            # call make post-processing
            make_id = None
            if item.get('make') != "":
                make_id = process_make(cursor, item.get('make'))

            if item.get('model') != "" and make_id is not None:
                process_model(cursor, item.get('model'), make_id)
        else:
            log.msg("[WARNING] Multiple Checking - %s" % item['url_id'], level=log.INFO)    

    def process_vin(self, cursor, item):
        """ update vin """

        if item.get('vin', None) is not None: 
            sql = "".join(("update ", item.get('site'), "_cars use index(idx_vin) set vin = %s where id = %s limit 1;"))
            parameters = (item.get('vin'), item.get('url_id'))

            cursor.execute(sql, parameters)
            cursor.execute("commit;")

            log.msg('[UPDATED VIN] %s - %s - %s at %s EST' % (item.get('site'), item.get('url_id'), item.get('vin'), datetime.now(timezone('US/Eastern'))
                        .strftime("%Y-%m-%d %H:%M:%S")), level=log.INFO)
        else:
            print item

    def handle_error(self, e):
        """
            rasing errors
        """
        log.err(e)
