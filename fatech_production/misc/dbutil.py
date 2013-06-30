#!/usr/bin/env python

#######################################
### Database Utility
#######################################

# Python import
from __future__ import with_statement
from datetime import datetime
from datetime import timedelta
import MySQLdb
import MySQLdb.cursors
from array import array
import random

# Custom imports
from fatech_production.settings import *

class DatabaseUtil(object):
    """ DatabaseUtil class """

    def __init__(self, site=None, spider=None):
        # name of the website
        self.site = site
        # name of the spider
        self.spider = spider

    def get_mysql_connection(self):
        """ get MySQL connection.
            return: A MySQL connection object
        """

        connection = MySQLdb.connect(
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            db=DATABASE_NAME,
            user=DATABASE_USER,
            passwd=DATABASE_PASSWORD,
            cursorclass=MySQLdb.cursors.DictCursor,
            charset='utf8',
            use_unicode=True
        )
        return connection

    def initialize_settings(self):
        """ initialize all default master_settings for a new website if needed """

        # Get a mysql connnection and a cursor to make queries 
        connection = self.get_mysql_connection()
        cursor = connection.cursor()

        # Concatenating sql string, join is faster than "+"
        sql = "".join(("select id from master_settings use index(idx_site) where site = %s;"))
        parameters = (self.site)
        # execution
        cursor.execute(sql, parameters)
        result = cursor.fetchone()

        if result is None:
            # the website is new, creating new tables for the website, 
            # including a new in master_settings table and three new tables of _cars, _urls, and _history. 

            # insert a new row for the website of the master_settings
            sql = "".join(("insert into master_settings(site) values(%s);"))
            parameters = (self.site)
            cursor.execute(sql, parameters)
            
            # create three new tables: _cars, _urls, _history 
            sql = "".join(("create table ", self.site, "_cars like template_cars;"))
            cursor.execute(sql)
            sql = "".join(("create table ", self.site, "_history like template_cars;"))
            cursor.execute(sql)
            sql = "".join(("create table ", self.site, "_urls like template_urls;"))
            cursor.execute(sql)

            # For making transactions affected
            cursor.execute("commit;")

        # Close connection for releasing resources                
        cursor.close()
        connection.close()  

    def write_settings(self, field, value):
        """ Update a new value for the field in the master_settings tables.
            parameters:
                field: must be an exact name of a column in the master_settings table
                value: a new value
        """

        connection = self.get_mysql_connection()
        cursor = connection.cursor()

        # concatenating update query
        sql = "".join(("update master_settings use index(idx_site) set ", field , "=%s where site = %s;"))
        parameters = (value, self.site)
        cursor.execute(sql, parameters)
        
        cursor.execute("commit;")

        cursor.close()
        connection.close()

    def load_settings(self, fields):
        """ Load specific fields in the master_settings table.
            parameters:
                fields: a string of fields (columns) list

            returns a dict of master_settings

            For example:
                fields = "active, cycles"
                output: {"active": 'F', "cycles": 1}
        """

        connection = self.get_mysql_connection()
        cursor = connection.cursor()

        # Concatenating the query string
        sql = "".join(("select ", fields, " from master_settings use index(idx_site) where site = %s;"))
        parameters = (self.site)
        
        cursor.execute(sql, parameters)
        result = cursor.fetchone()

        cursor.close()
        connection.close()
        
        return result
    
    def get_checking_urls(self, old_days, block_size, offset, status, new_status):
        
        """ get a block_size of url_ids of the status(E or H)

            for each selected url_id
                if inserted_at is older than old_days then
                    update url_id status to H if status is E, otherwise update status to D 
                otherwise,
                    append url_ids into result_set

            return: a arrays of rechecking url_ids

        """

        connection = self.get_mysql_connection()
        cursor = connection.cursor()

        # Convert old_days to datetime
        old_days = int(old_days)
        #old_time = datetime.now() - timedelta(days=old_days)

        # initialize result array
        url_ids = array('i')

        sql = "".join(("select count(*) as quantity from ", self.site, "_urls use index(idx_status, idx_inserted_at) where status = %s and \
            inserted_at between DATE_SUB(NOW(), INTERVAL %s DAY) and NOW();"))
        parameters = (status, old_days)
        cursor.execute(sql, parameters)
        quantity = cursor.fetchone()['quantity']
        offset = 0
        while offset < quantity:
            # Concatenating query
            sql = "".join(("select id from ", self.site, "_urls use index(idx_status, idx_inserted_at) where status = %s and \
                inserted_at between DATE_SUB(NOW(), INTERVAL %s DAY) and NOW() limit %s, %s;"))
            parameters = (status, old_days, offset, block_size)
            # Execution
            cursor.execute(sql, parameters)
            rows = cursor.fetchall()

            for row in rows:
                url_ids.insert(-1, row['id'])

            offset += len(rows)

        # for row in rows:
        #     # if the id is newer than old_days
        #     if row['inserted_at'] > old_time:
        #         # add to result array
        #         url_ids.insert(-1, row['id'])
        #     else:
        #         # update the id with new status
        #         sql = "".join(("update ", self.site, "_urls set status = %s where id = %s limit 1;"))
        #         parameters = (new_status, int(row['id']))                    
        #         cursor.execute(sql, parameters)
    
        # cursor.execute('commit;')
        
        cursor.close()
        connection.close()

        # Shuffle the result array
        random.shuffle(url_ids)

        return url_ids

    def get_ids_for_vin(self, block_size):
        """ get url_ids to get vins """

        connection = self.get_mysql_connection()
        cursor = connection.cursor()

        sql = "".join(("select id from ", self.site, "_cars use index(idx_vin) where vin is NULL limit %s;"))
        parameters = (block_size)
        cursor.execute(sql, parameters)
        rows = cursor.fetchall()
        url_ids = array('i')
        for row in rows:
            url_ids.insert(-1, row['id']) 

        cursor.close()
        connection.close()

        return url_ids

    def get_all_models(self, make):
        """ retrieve all models of the make from the year_make_model table.
            return: a tuple of models
        """

        # result tuple
        all_models = tuple()

        connection = self.get_mysql_connection()
        cursor = connection.cursor()

        ### count the number of models of the make
        sql = "select count(*) as quantity from year_make_model use index(idx_make) where make = %s;"
        parameters = (make)
        cursor.execute(sql, parameters)
        quantity = cursor.fetchone()['quantity']
        offset = 0
        ### Make queries to get all expected models
        while  offset < quantity:
            sql = "select model from year_make_model use index(idx_make) where make= %s limit %s, 100;"
            parameters = (make, offset)
            cursor.execute(sql, parameters)
            rows = cursor.fetchall()
            # concatenating models into the result tuple
            all_models += tuple(row['model'] for row in rows)

            # update new offset value
            offset += len(rows)

        cursor.close()
        connection.close()

        return all_models

    # def get_standard_makes(self):
    #     all_makes = tuple()

    #     connection = self.get_mysql_connection()
    #     cursor = connection.cursor()

    #     sql = "select count(*) as quantity from master_makes_variations;"
    #     parameters = ()
    #     cursor.execute(sql, parameters)
    #     quantity = cursor.fetchone()['quantity']
    #     offset = 0
    #     while  offset < quantity:
    #         sql = "select make from master_makes_variations limit %s, 100;"
    #         parameters = (make, offset)
    #         cursor.execute(sql, parameters)
    #         rows = cursor.fetchall()
    #         all_models += tuple(row['make'] for row in rows)

    #         # update new offset value
    #         offset += len(rows)

    #     cursor.close()
    #     connection.close()

    #     return all_models

# def get_proxies():
#     """
#         get proxies to perform requesting
#         returns a list of available proxies
#     """

#     proxies = []
#     connection = get_mysql_connection()
#     cursor = connection.cursor()

#     # get a third octet
#     cursor.execute(
#         "select third_octet from third_octets use index(idx_status) where status = 'A' order by rand() limit 1;"
#     )
#     result = cursor.fetchone()
#     if result:
#         third_octet = result['third_octet']
#     else:
#         cursor.execute(
#             "select proxy from proxies order by rand() limit 1;"
#         )
#         result = cursor.fetchone()
#         third_octet = result['third_octet']

#     # get proxies which have the above third octet
#     cursor.execute(
#         "select proxy from proxies where third_octet = '%s' order by rand() limit 100;", (third_octet)
#     )
#     rows = cursor.fetchall()
#     proxies = [row['proxy'] for row in rows]

#     # update third octet is in used
#     cursor.execute(
#         "update third_octets use index (idx_third_octet) set status = 'I' where third_octet = %s limit 1;", (third_octet)
#     )
#     cursor.execute('commit;')

#     cursor.close()
#     connection.close()

#     return proxies


# def get_third_octet(proxy):
#     """
#         get the third octet of a proxy
#         input: a string of proxy
#         output: a string of the third octet

#         For example:
#             input: 173.232.7.134:8800
#             output: 7
#     """
#     return proxy.split('.')[-2]


# def release_proxies(proxy):
#     """
#         change proxies' status from "in-used" to "available"
#     """

#     connection = get_mysql_connection()
#     cursor = connection.cursor()

#     third_octet = get_third_octet(proxy)
#     cursor.execute(
#         "update third_octets use index (idx_third_octet) set status = 'A' where third_octet = %s limit 1;", (third_octet)
#     )
#     cursor.execute('commit;')
#     cursor.close()
#     connection.close()
