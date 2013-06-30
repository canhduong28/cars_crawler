#!/usr/bin/env python

#######################################
### Define Scrapy Items
#######################################

from scrapy.item import Item, Field

### Link Item ###
class Link(Item):
    url = Field()
    url_id = Field()
    status = Field()
    #spider = Field()
    site = Field()

### Car Item ###
class Car(Item):
    site = Field()
    description = Field()
    year = Field()
    make = Field()
    model = Field()
    trim = Field()
    price = Field()
    body_style = Field()
    exterior_color = Field()
    interior_color = Field()
    engine = Field()
    stock_id = Field()
    vin = Field()
    mileage = Field()
    transmission = Field()
    drive_type = Field()
    doors = Field()
    fuel_type = Field()
    cab_type = Field()
    stereo = Field()
    dealer = Field()
    street_number = Field()
    street_name = Field()
    city = Field()
    state = Field()
    zip_code = Field()
    phone = Field()
    source_url = Field()
    url_id = Field()
    found_by = Field()
    pass

### Vin Item ###
class Vin(Item):
    site = Field()
    url_id = Field()
    vin = Field()
    pass
