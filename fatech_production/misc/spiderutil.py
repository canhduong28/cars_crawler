#!/usr/bin/env python

#######################################
### Spider Utility for generating recon IDs, 
### extracting year, make, model, price...  
#######################################

# Python imports
import re
from dbutil import DatabaseUtil

def generate_ids(site):
    """ Generate ids for recon spider """

    from array import array
    
    # Load settings of recon_startid, block_size, cycles, cycles_limit, overs
    settings = DatabaseUtil(site).load_settings(fields="recon_startid, block_size, cycles, cycles_limit, overs")
    # pass settings to variables
    old_startid = int(settings['recon_startid']) + 1
    cycles = int(settings['cycles'])
    cycles_limit = int(settings['cycles_limit'])
    block_size = int(settings['block_size'])
    overs = int(settings['overs'])

    if cycles >= cycles_limit:
        overs += 1

    if cycles / 100 > 0:
        cycles = cycles / 100
        
    # Get the 10's place digit for cycles
    cycles1 = cycles % 10

    # Get the 100's place digit from cycles
    cycles2 = (cycles /10) % 10

    # How many ID's to skip
    skip  = 17

    # Where the new spider starts. Use cycles1 to determine which 10's digit to scan
    new_startid = int(old_startid + cycles1)

    # How far to jump ahead. Use cycles2 to determine how far out to recon
    recon_startid = int(new_startid + cycles2 * block_size)

    # Pretty obvious
    end_id = int(recon_startid + block_size)

    # Number of cycles before going back and checking the very first range again
    backcheck = 5

    # Create array (less memory than a list) of integers to generate urls from
    recon_list = array('i',(xrange(recon_startid, end_id, skip)))

    # If cycles are more that 50, then double back and check the first group without jumping
    # Dived the skip number by 2 to double the intensity of check the first block
    if cycles >= backcheck:
        backcheck_list = array('i',(xrange(new_startid, new_startid + skip/2, skip)))
        recon_list.extend(backcheck_list)

    recon_list = array('i', (id + overs for id in recon_list))

    # update a new overs if it needed
    if overs != int(settings['overs']):
        if overs > 10:
            overs = 0
        DatabaseUtil(site).write_settings(field="overs", value=overs)


    return recon_list

def get_ids_for_vin(site, block_size):
    """ get url_ids to get vins """

    return DatabaseUtil(site).get_ids_for_vin(block_size)
    
def doors_tostring(data):
    """ convert doors format from an integer to a string.
        input: a string of digit
        output: a string in natural text (English)

        Examples:
            input: 1
            output: One Door

            input: 2
            output: Two Door
            ...
    """

    return {
        '1': 'One Door',
        '2': 'Two Door',
        '3': 'Three Door',
        '4': 'Four Door',
        '5': 'Five Door',
        '6': 'Six Door',
        '7': 'Seven Door',
        '8': 'Eight Door',
        '9': 'Nine Door'
    }.get(data, data)

def generate_ngrams(data):
    """ generate a list of grams from model's data so that matching model's data with default model from library database.
        input: a string
        output: a tuple of strings

        For example:
            input: "Accent GLS Sedan"
            output: ["Accent", "GLS", "Sedan", "Accent GLS", "GLS Seda", "Accent GLS Sedan"]
            ...
    """
    # Get unigrams
    unigrams = data.split()
    # Convert into tuple for saving memory
    ngrams = tuple(unigrams)
    # The length of the gram
    n = len(unigrams) if len(unigrams) < 3 else 3
    # Generate bigrams
    ngrams += tuple("".join((unigrams[i], ' ', unigrams[i+1])) for i in xrange(len(unigrams)-1))
    # Generate trigrams
    ngrams += tuple("".join((unigrams[i], ' ', unigrams[i+1], ' ', unigrams[i+2])) for i in xrange(len(unigrams)-2))
    
    return ngrams

def extract_YMMT(data):
    """
        parse description to get year, make, model and trim from the description
        returns a dict of them or -1 if not found any make
    """

    # a hard-coded list of makes to match make in description
    standard_makes = (
        'Acura', 'Alfa Romeo', 'AMC', 'Aston Martin',
        'Audi', 'Avanti', 'Bentley', 'BMW', 'Buick',
        'Cadillac', 'Chevrolet', 'Chrysler', 'Daewoo',
        'Daihatsu', 'Datsun', 'DeLorean', 'Dodge', 'Eagle',
        'Ferrari', 'Fiat', 'Fisker', 'Ford', 'Freightliner',
        'Geo', 'GMC', 'Honda', 'Hummer', 'Hyundai',
        'Infiniti', 'Isuzu', 'Jaguar', 'Jeep', 'Kia',
        'Lamborghini', 'Lancia', 'Land Rover', 'Lexus',
        'Lincoln', 'Lotus', 'Maserati', 'Maybach', 'Mazda',
        'McLaren', 'Mercedes-Benz', 'Mercury', 'Merkur',
        'Mini', 'Mitsubishi', 'Nissan', 'Oldsmobile',
        'Peugeot', 'Plymouth', 'Pontiac', 'Porsche',
        'Renault', 'Rolls-Royce', 'Saab', 'Saturn', 'Scion',
        'Smart', 'SRT', 'Sterling', 'Subaru', 'Suzuki',
        'Tesla', 'Toyota', 'Triumph', 'Volkswagen', 'Volvo', 
        'Yugo', 'Ram',

    )
    
    # looking for the year in the description
    year = re.search(r'(\d+)', data).group(1)

    make = None
    # looking for make in the manual list
    for m in standard_makes:
        if m in data:
            make = m
            break
        elif m.upper() in data:
            make = m.upper()
            break
    if not make:
        # Can't found any make, exit the method here
        return -1

    data = data.replace(year, '', 1)
    data = data.replace(make, '', 1).strip()

    model = ""
    trim = ""
    # Generate all ngrams from the description to match make and model pair
    ngrams = generate_ngrams(data)

    # Load all models of the make from the DB
    all_models = DatabaseUtil().get_all_models(make)
    
    for gram in ngrams:
        found = False
        for each in all_models:
            # try to match make from the description with one of them in the DB
            if each.lower().strip() == gram.lower().strip():
                model = gram
                # Extract trim after model's place
                try:
                    trim = re.search(model + r'(.+)', data).group(1).strip()
                except:
                    pass
                found = True
                break
        if found:
            break
        
    return {'year': year, 'make': make.strip(), 'model': model.strip(), 'trim': trim.strip()}

def extract_price(data):
    """
        get price in decimal
    """

    try:
        price = re.search(r'([0-9\,\.]+)', data).group(1)
        return price
    except:
        return "-1"

def extract_mileage(data):
    """ get mileage in decimal """

    try:
        mileage = re.search(r'([0-9\,\.]+)', data).group(1)
        return mileage
    except:
        return "-1"

def extract_phone(data):
    """ get phone number from text """

    try:
        phone = re.search(r'([0-9-]+)', data).group(1)
        return phone
    except:
        return ""

def extract_street(data):
    """
        extract street_number and street_name
        return a dict of street_number, and street_name
    """

    try:
        street_number = re.search(r'([0-9\-]+)\s', data).group(1)
        street_name = data.replace(street_number, '', 1).strip()
        return {'street_number': street_number, 'street_name': street_name}
    except:
        return {'street_number': "", 'street_name': data.strip()}

def extract_CSZ(data):
    """
        extract city, state, and zip_code in the address
        returns a dict of city, state, and zip_code
    """

    try:
        city = re.search(r'(.+)\,', data).group(1)
    except:
        city = ""

    try:
        state = re.search(r'\,\s+([A-Z]{2})', data).group(1)
    except:
        state = ""
    
    try:
        zip_code = re.search(r'[A-Z]{2}\s+(\d+)', data).group(1)
    except:
        zip_code = "-1"

    return {'city': city, 'state': state, 'zip_code': zip_code}

