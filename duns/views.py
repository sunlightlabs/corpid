import lxml.etree
from urllib import urlencode, quote
from urllib2 import urlopen
try:
    import json
except ImportError:
    import simplejson as json
from operator import itemgetter
from django.http import HttpResponse, HttpResponseServerError, Http404
from django.shortcuts import render, render_to_response, redirect, get_object_or_404
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from duns.models import FPDS, FAADS, DUNS, Name
from utils import parseint

PSCCategoryLabels = {
    "10": "WEAPONS",
    "11": "NUCLEAR ORDNANCE",
    "12": "FIRE CONTROL EQPT.",
    "13": "AMMUNITION AND EXPLOSIVES",
    "14": "GUIDED MISSLES",
    "15": "AIRCRAFT/AIRFRAME STRUCTURE COMPTS",
    "16": "AIRCRAFT COMPONENTS/ACCESSORIES",
    "17": "AIRCRAFT LAUNCH/LAND/GROUND HANDLE",
    "18": "SPACE VEHICLES",
    "19": "SHIPS, SMALL CRAFT, PONTOON, DOCKS",
    "20": "SHIP AND MARINE EQUIPMENT",
    "22": "RAILWAY EQUIPMENT",
    "23": "MOTOR VEHICLES, CYCLES, TRAILERS",
    "24": "TRACTORS",
    "25": "VEHICULAR EQUIPMENT COMPONENTS",
    "26": "TIRES AND TUBES",
    "28": "ENGINES AND TURBINES AND COMPONENT",
    "29": "ENGINE ACCESSORIES",
    "30": "MECHANICAL POWER TRANSMISSION EQPT",
    "31": "BEARINGS",
    "32": "WOODWORKING MACHINERY AND EQPT",
    "34": "METALWORKING MACHINERY",
    "35": "SERVICE AND TRADE EQPT",
    "36": "SPECIAL INDUSTRY MACHINERY",
    "37": "AGRICULTURAL MACHINERY AND EQPT",
    "38": "CONSTRUCT/MINE/EXCAVATE/HIGHWY EQPT",
    "39": "MATERIALS HANDLING EQPT",
    "40": "ROPE, CABLE, CHAIN, FITTINGS",
    "41": "REFRIG, AIR CONDIT/CIRCULAT EQPT",
    "42": "FIRE/RESCUE/SAFETY; ENVIRO PROTECT",
    "43": "PUMPS AND COMPRESSORS",
    "44": "FURNACE/STEAM/DRYING; NUCL REACTOR",
    "45": "PLUMBING, HEATING, WASTE DISPOSAL",
    "46": "WATER PURIFICATION/SEWAGE TREATMENT",
    "47": "PIPE, TUBING, HOSE, AND FITTINGS",
    "48": "VALVES",
    "49": "MAINT/REPAIR SHOP EQPT",
    "51": "HAND TOOLS",
    "52": "MEASURING TOOLS",
    "53": "HARDWARE AND ABRASIVES",
    "54": "PREFAB STRUCTURES/SCAFFOLDING",
    "55": "LUMBER, MILLWORK, PLYWOOD, VENEER",
    "56": "CONSTRUCTION AND BUILDING MATERIAL",
    "58": "COMM/DETECT/COHERENT RADIATION",
    "59": "ELECTRICAL/ELECTRONIC EQPT COMPNTS",
    "60": "FIBER OPTIC",
    "61": "ELECTRIC WIRE, POWER DISTRIB EQPT",
    "62": "LIGHTING FIXTURES, LAMPS",
    "63": "ALARM, SIGNAL, SECURITY DETECTION",
    "65": "MEDICAL/DENTAL/VETERINARY EQPT/SUPP",
    "66": "INSTRUMENTS AND LABORATORY EQPT",
    "67": "PHOTOGRAPHIC EQPT",
    "68": "CHEMICALS AND CHEMICAL PRODUCTS",
    "69": "TRAINING AIDS AND DEVICES",
    "70": "ADP EQPT/SOFTWARE/SUPPLIES AND EQPT",
    "71": "FURNITURE",
    "72": "HOUSEHOLD/COMMERC FURNISH/APPLIANCE",
    "73": "FOOD PREPARATION/SERVING EQPT",
    "74": "OFFICE MACH/TEXT PROCESS/VISIB REC",
    "75": "OFFICE SUPPLIES AND DEVICES",
    "76": "BOOKS, MAPS, OTHER PUBLICATIONS",
    "77": "MUSICAL INST/PHONOGRAPH/HOME RADIO",
    "78": "RECREATIONAL/ATHLETIC EQPT",
    "79": "CLEANING EQPT AND SUPPLIES",
    "80": "BRUSHES, PAINTS, SEALERS, ADHESIVES",
    "81": "CONTAINERS/PACKAGING/PACKING SUPPL",
    "83": "TEXTILE/LEATHER/FUR; TENT; FLAG",
    "84": "CLOTHING/INDIVIDUAL EQPT, INSIGNIA",
    "85": "TOILETRIES",
    "87": "AGRICULTURAL SUPPLIES",
    "88": "LIVE ANIMALS",
    "89": "SUBSISTENCE",
    "91": "FUELS, LUBRICANTS, OILS, WAXES",
    "93": "NONMETALLIC FABRICATED MATERIALS",
    "94": "NONMETALLIC CRUDE MATERIALS",
    "95": "METAL BARS, SHEETS, SHAPES",
    "96": "ORES, MINERALS AND PRIMARY PRODUCTS",
    "99": "MISCELLANEOUS",
    "A": "RESEARCH AND DEVELOPMENT",
    "B": "SPECIAL STUDIES/ANALYSIS, NOT RANDD",
    "C": "ARCHITECT/ENGINEER SERVICES",
    "D": "ADP AND TELECOMMUNICATIONS",
    "E": "PURCHASE OF STRUCTURES/FACILITIES",
    "F": "NATURAL RESOURCES MANAGEMENT",
    "G": "SOCIAL SERVICES",
    "H": "QUALITY CONTROL, TEST, INSPECTION",
    "J": "MAINT, REPAIR, REBUILD EQUIPMENT",
    "K": "MODIFICATION OF EQUIPMENT",
    "L": "TECHNICAL REPRESENTATIVE SVCS.",
    "M": "OPERATION OF GOVT OWNED FACILITY",
    "N": "INSTALLATION OF EQUIPMENT",
    "P": "SALVAGE SERVICES",
    "Q": "MEDICAL SERVICES",
    "R": "SUPPORT SVCS (PROF, ADMIN, MGMT)",
    "S": "UTILITIES AND HOUSEKEEPING",
    "T": "PHOTO, MAP, PRINT, PUBLICATION",
    "U": "EDUCATION AND TRAINING",
    "V": "TRANSPORT, TRAVEL, RELOCATION",
    "W": "LEASE/RENT EQUIPMENT",
    "X": "LEASE/RENT FACILITIES",
    "Y": "CONSTRUCT OF STRUCTURES/FACILITIES",
    "Z": "MAINT, REPAIR, ALTER REAL PROPERTY"
}

NameBlacklist = [
    'NO DATA FROM D AND B',
    'ENVIRONMENTAL PROTECTION AGENCY',
    'MISCELLANEOUS FOREIGN CONTRACT',
    'MISCELLANEOUS FOREIGN CONTRACTORS',
    'J & B TRUCK REPAIR SERVICE',
]

DUNSBlacklist = [
    '0000000000000', # 'ENVIRONMENTAL PROTECTION AGENCY', & others
    '5571630810000', # 'ENVIRONMENTAL PROTECTION AGENCY', & others
    '7777777770000',
    '1234567870000'  # 'MISCELLANEOUS FOREIGN CONTRACTORS', & others
]

def index(request):
    contract_count = FPDS.objects.count()
    grant_count = FAADS.objects.count()
    name_count = Name.objects.count()
    duns_count = DUNS.objects.count()

    return render_to_response('duns-index.html',
                              { 'contract_count': contract_count,
                                'grant_count': grant_count,
                                'name_count': name_count,
                                'duns_count': duns_count })

def search_by_name(entity_name):
    if entity_name.upper() in NameBlacklist:
        return None

    try:
        nm = Name.objects.get(name=entity_name)
        grants = nm.faads.all()
        contracts = nm.fpds.all()
        duns_numbers = set( [g.duns.number for g in grants]
                          + [c.duns.number for c in contracts] )
        return [n for n in duns_numbers
                  if parseint(n, 0) != 0]
    except Name.DoesNotExist:
        return None


def search_by_duns(duns_number):
    if duns_number in DUNSBlacklist:
        return None

    try:
        duns = DUNS.objects.get(number=duns_number)
        grants = duns.faads.all()
        contracts = duns.fpds.all()
        names = set( [g.recipient_name.name.upper() for g in grants] 
                   + [c.company_name.name.upper() for c in contracts] )
        return list(names)
    except DUNS.DoesNotExist:
        return None


def lookup_by_name(request, entity_name):
    cache_key = quote(entity_name.upper())
    duns_list = cache.get(cache_key)
    print "%s cache %s" % (cache_key, "hit" if duns_list else "miss")
    if duns_list is None:
        duns_list = search_by_name(entity_name)
        if duns_list is None:
            duns_list = []
        else:
            cache.set(cache_key, duns_list)
    json_string = json.dumps({'querytype': 'name',
                              'query': entity_name,
                              'results': duns_list})
    return HttpResponse(json_string, mimetype='application/json')


def lookup_by_duns_number(request, duns_number):
    cache_key = quote(duns_number)
    name_list = cache.get(cache_key)
    print "%s cache %s" % (cache_key, "hit" if name_list else "miss")
    if name_list is None:
        name_list = search_by_duns(duns_number)
        if name_list is None:
            name_list = []
        else:
            cache.set(cache_key, name_list)
    json_string = json.dumps({'querytype': 'duns',
                              'query': duns_number,
                              'results': name_list})
    return HttpResponse(json_string, mimetype='application/json')


def node_details(contracts, grants):
    contract_details_getter = lambda c: {'duns': c.duns.number,
                                         'company_name': c.company_name.name,
                                         'fiscal_year': c.fiscal_year,
                                         'unique_transaction_id': c.unique_transaction_id,
                                         'piid': c.piid,
                                         'psc_category_label': PSCCategoryLabels.get(c.psc_category, '')}
    contract_details = [contract_details_getter(c) for c in contracts]

    grant_details_getter = lambda g: {'duns': g.duns.number,
                                      'recipient_name': g.recipient_name.name,
                                      'fiscal_year': g.fiscal_year,
                                      'unique_transaction_id': g.unique_transaction_id,
                                      'federal_award_id': g.federal_award_id,
                                      'federal_award_mod': g.federal_award_mod,
                                      'obligation_action_date': g.obligation_action_date.isoformat()}
    grant_details = [grant_details_getter(g) for g in grants]
    return (contract_details, grant_details)


def autocomplete(request):
    term = request.GET.get('term')
    if term is not None:
        names = [n.name for n in Name.objects.filter(name__startswith=request.GET.get('term'))]
    else:
        names = []
    return HttpResponse(json.dumps(names), 'application/json')

def name_details(request, fmt, entity_name):
    try:
        name = Name.objects.get(name=entity_name)
        contracts = name.fpds.all()
        grants = name.faads.all()
        (contract_details, grant_details) = node_details(contracts, grants)
        params = {'querytype': 'namedetails',
                  'name': entity_name,
                  'contracts': contract_details,
                  'grants': grant_details}
        if fmt == 'html':
            return render_to_response('name_details_snippet.html', params)
        else:
            json_string = json.dumps(params)
            return HttpResponse(json_string, mimetype='application/json')
    except Name.DoesNotExist:
        raise Http404(entity_name)

def duns_details(request, fmt, duns_number):
    try:
        duns = DUNS.objects.get(number=duns_number)
        contracts = duns.fpds.all()
        grants = duns.faads.all()
        (contract_details, grant_details) = node_details(contracts, grants)
        params = {'querytype': 'dunsdetails',
                  'duns': duns_number,
                  'contracts': contract_details,
                  'grants': grant_details}
        if fmt == 'html':
            return render_to_response('duns_details_snippet.html', params)
        else:
            json_string = json.dumps(params)
            return HttpResponse(json_string, mimetype='application/json')
    except DUNS.DoesNotExist:
        return None
        
