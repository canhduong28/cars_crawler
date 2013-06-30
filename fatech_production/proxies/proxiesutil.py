#!/usr/bin/env python

#######################################
### Database Utility
#######################################

# Python imports
import MySQLdb
import MySQLdb.cursors
import sys
from datetime import datetime
from datetime import timedelta

# Custom imports
from fatech_production.settings import *

class ProxiesUtil(object):

    def __init__(self):
        pass

    def get_mysql_connection(self):
        """ return a mysql connection """

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

    def get_third_octet(self, proxy):
        """
            get the third octet of a proxy
            input: a string of proxy
            output: a string of the third octet

            For example:
                input: 173.232.7.134:8800
                output: 7
        """
        return proxy.split('.')[-2]


    def check_third_octet(self, cursor, third_octet):
        """
            checking if third_octet exists in the database
            returns True if it exists, otherwise, return False
        """
        
        cursor.execute(\
            "select id from third_octets use index(idx_third_octet) where third_octet = %s;", (third_octet)
        )
        result = cursor.fetchone()
        if result:
            return True
        else:
            return False

    def add_third_octet(self, cursor, third_octet):
        """
            add a new third_octet
        """

        cursor.execute(\
            "insert into third_octets(third_octet) values (%s)", (third_octet)
        )

    def read_input(self, file_path):
        """
            read proxies from input file
            returns two parameters, an account and a list of proxies
        """

        proxies = []
        f = open(file_path, 'rb')
        line = f.readline().strip()
        account = line.split('=')[1]
        while line:
            line = f.readline().strip()
            if line:
                proxies.append(line)
        f.close()

        return account, proxies

    def check_proxy(self, cursor, proxy):
        """
            Check a proxy if it exists
            returns True if exists, otherwise, returns False
        """
        
        cursor.execute(\
            'select id from master_proxies use index (idx_proxy) where proxy = %s;', (proxy)
        )
        result = cursor.fetchone()
        if result:
            return True
        else:
            return False

    def add_proxy(self, cursor, proxy, third_octet, account):
        """ Add a new proxy """

        cursor.execute(
            'insert into master_proxies(proxy, third_octet, account) values (%s, %s, %s)', (proxy, third_octet, account)
        )

    def release_proxies(self, hours=1):
        connection = self.get_mysql_connection()
        cursor = connection.cursor()

        old_time = datetime.now() - timedelta(minutes=hours)

        cursor.execute(\
            "select id, updated_at from third_octets use index (idx_status) where status = 'I' limit 100;"
        )
        rows = cursor.fetchall()
        for row in rows:
            if row['updated_at'] < old_time:
                cursor.execute(\
                    "update third_octets set status = 'A' where id = %s limit 1;", (str(row['id']))
                )
        cursor.execute("commit;")
        cursor.close()
        connection.close()

    def import_proxies(self, input_path):
        connection = self.get_mysql_connection()
        cursor = connection.cursor()

        account, proxies = self.read_input(input_path)
        for proxy in proxies:
            third_octet = self.get_third_octet(proxy)
            if not self.check_third_octet(cursor, third_octet):
                self.add_third_octet(cursor, third_octet)
            if not self.check_proxy(cursor, proxy):
                self.add_proxy(cursor, proxy, third_octet, account)

        cursor.execute("commit;")
        cursor.close()
        connection.close()

    def get_proxy(self):
        connection = self.get_mysql_connection()
        cursor = connection.cursor()
        cursor.execute("select proxy from master_proxies order by rand() limit 1;")
        try:
            proxy = cursor.fetchone()['proxy']
        except:
            proxy = ""
        cursor.close()
        connection.close()

        return proxy

if __name__ == "__main__":
    argv = sys.argv

    if len(argv) < 2:
        print "[USEAGE] python proxiesutil.py [method] [input_file]"
        sys.exit(1)
    method = argv[1]
    if method == "import":
        input_file = argv[2]
        ProxiesUtil().import_proxies(input_file)
    elif method == "release":
        ProxiesUtil().release_proxies()
    elif method == 'get':
        print ProxiesUtil().get_proxy()