#!/usr/bin/env python

#######################################
### Setting Classes for specific Spiders
#######################################

# Python import
from __future__ import with_statement
import os

# Custom imports
from fatech_production.settings import *
from dbutil import DatabaseUtil

class SpiderSettings(object):
    """ Base class for Spider Settings """
    
    def __init__(self, site, spider):
        # name of the website
        self.site = site
        # name of the spider
        self.spider = spider
        
    def initialize_settings(self):
        """ initial settings for a new site """
        
        DatabaseUtil(self.site, self.spider).initialize_settings()

    def load_settings(self):
        pass

    def write_active(self, setting):
        """ write status of activating """

        # if spider is recheck of finalcheck
        if 'check' in self.spider:
            active_field = 'recheck_active'
        else:
            # spder is recon or main
            active_field = 'active'

        # Call write_settings method to make transaction 
        DatabaseUtil(self.site, self.spider).write_settings(field=active_field, value=setting)

class ReconSpiderSettings(SpiderSettings):
    """ Settings for Recon Spider, inherited from default SpiderSettings """

    def __init__(self, site, spider='recon'):
        super(ReconSpiderSettings, self).__init__(site, spider)

    def load_settings(self):
        """ Load recon spider settings (active, block_size, cycles, main_startid, recon_startid) from last spider run. \
        Grab defaults if none are present, returns a dict of settings

        """

        settings = DatabaseUtil(self.site, self.spider).load_settings(fields="active, block_size, cycles, main_startid, recon_startid")
        return {'active': settings['active'], 'block_size': int(settings['block_size']), 'cycles': int(settings['cycles']), \
            'main_startid': int(settings['main_startid']), 'recon_startid': int(settings['recon_startid'])}
        
    def write_cycles(self, setting):
        """ Write the cycles setting for this run of the spider """

        DatabaseUtil(self.site, self.spider).write_settings(field="cycles", value=setting)
            
    def write_startid(self, setting):
        """ Write the new startid setting for this run of the spider """

        DatabaseUtil(self.site, self.spider).write_settings(field="recon_startid", value=setting)
    
class MainSpiderSettings(SpiderSettings):
    """ Settings for Main Spider, inherited from default SpiderSettings """

    def __init__(self, site, spider='main'):
        super(MainSpiderSettings, self).__init__(site, spider)

    def load_settings(self):
        """ Load settings (active, block_size, main_startid, recon_startid) from last spider run. \
        Grab defaults if none are present, returns a dict of settings
        """

        settings = DatabaseUtil(self.site, self.spider).load_settings(fields="active, block_size, main_startid, recon_startid")
        return {'active': settings['active'], 'block_size': int(settings['block_size']), 'main_startid': int(settings['main_startid']),\
            'recon_startid': int(settings['recon_startid'])}

    def write_startid(self, setting):
        """ Write the new startid setting for this run of the spider """

        DatabaseUtil(self.site, self.spider).write_settings(field="main_startid", value=setting)
    
class RecheckSpiderSettings(SpiderSettings):
    """ Settings for Recheck Spider, inherited from default SpiderSettings """

    def __init__(self, site, spider='recheck'):
        super(RecheckSpiderSettings, self).__init__(site, spider)
     
    def load_settings(self):
        """ Load settings (recheck_active, recheck_olddays, block_size) from last spider run. \
        Grab defaults if none are present, return a dict of settings
        """

        settings = DatabaseUtil(self.site, self.spider).load_settings(fields="recheck_active, recheck_olddays, block_size")
        return {'active': settings['recheck_active'], 'block_size': settings['block_size'], 'url_ids': self.get_recheck_urls(settings['recheck_olddays'], settings['block_size'])}

    def get_recheck_urls(self, old_days, block_size):
        """ Get a block_size of rechecking URLs which adapt old_days constrain, returns an array of url_ids """

        def get_recheck_offset():
            """ Get the recheck offset from the last spider run """

            settings = DatabaseUtil(self.site, self.spider).load_settings(fields="recheck_offset")
            return int(settings['recheck_offset'])

        def write_recheck_offset(setting):
            """ Write the recheck offset for this run of the spider """

            DatabaseUtil(self.site, self.spider).write_settings(field="recheck_offset", value=setting)

        # call inner method to get recheck_offset
        recheck_offset = get_recheck_offset()
        url_ids = DatabaseUtil(self.site, self.spider).get_checking_urls(old_days, block_size, recheck_offset, 'E', 'H')
        # if any accepted url_id
        if len(url_ids) > 0:
            # call inner method update a new recheck offset
            write_recheck_offset(recheck_offset + len(url_ids))
        else:
            # call inner method to reset recheck offset
            write_recheck_offset(0)

        return url_ids

class FinalcheckSpiderSettings(SpiderSettings):
    """ Settings for Finalcheck Spider, inherited from default SpiderSettings """

    def __init__(self, site, spider='finalcheck'):
        super(FinalcheckSpiderSettings, self).__init__(site, spider)
     
    def load_settings(self):
        """ Load settings (recheck_active, finalcheck_olddays, block_size) from last finalcheck spider run. \
        Grab defaults if none are present, returns a dict of settings 
        """

        settings = DatabaseUtil(self.site, self.spider).load_settings(fields="recheck_active, finalcheck_olddays, block_size")
        return {'active': settings['recheck_active'], 'url_ids': self.get_finalcheck_urls(settings['finalcheck_olddays'], settings['block_size'])}

    def get_finalcheck_urls(self, old_days, block_size):
        """ Get a block_size of rechecking URLs which adapt old_days constrain, returns an array of url_ids """

        def get_finalcheck_offset():
            """ Get the finalcheck offset from the last spider run """

            settings = DatabaseUtil(self.site, self.spider).load_settings(fields="finalcheck_offset")
            return int(settings['finalcheck_offset'])

        def write_finalcheck_offset(setting):
            """ Write the finalcheck offset for this run of the spider """

            DatabaseUtil(self.site, self.spider).write_settings(field="finalcheck_offset", value=setting)

        # call inner method to get finalcheck_offset
        finalcheck_offset = get_finalcheck_offset()
        url_ids = DatabaseUtil(self.site, self.spider).get_checking_urls(old_days, block_size, finalcheck_offset, 'H', 'D')
        # if any accepted url_id
        if len(url_ids) > 0:
            # call inner method update a new finalcheck offset
            write_finalcheck_offset(finalcheck_offset + len(url_ids))
        else:
            # call inner method to reset finalcheck offset
            write_finalcheck_offset(0)

        return url_ids
