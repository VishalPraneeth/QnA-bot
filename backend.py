import os
import json
import logging
import datetime
from operator import itemgetter
import boto3
from boto3.dynamodb.conditions import Key, Attr
import asyncio


# Initialize Logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def set_global_vars():
    """
    Set the Global Variables
    If User provides different values, override defaults
    This function returns the AWS account number
    :return: global_vars
    :rtype: dict
    """
    global_vars = {'status': False, 'error_message': ''}
    try:
        global_vars['Owner']                = "Miztiik"
        global_vars['Environment']          = "Test"
        global_vars['region_name']          = "us-east-1"
        global_vars['tag_key']              = "Valaxy-HelpDesk-Bot"
        global_vars['faq_db_fname']         = "./data/val.json"
        global_vars['ddb_table_name']       = "valaxy-butler-queries"
        global_vars['update_ddb']           = True
        global_vars['status']               = True
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")
    return global_vars


def resp_chk(resp_status: bool, resp_err: str):
    # Check and continue if no errors
    if not resp_status:
        logger.error(f"ERROR: {resp_err}")


def read_from_file(filename):
    with open(filename) as json_file:
        data = json.load(json_file)
    return data


def safe_div(n, d):
    return n / d if d else 0

def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def elicit_slot_w_response(session_attributes, intent_name, slots, slot_to_elicit, message, response_card):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message,
            'responseCard': response_card
        }
    }


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

def confirm_intent(session_attributes, intent_name, slots, message, response_card):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message,
            'responseCard': response_card
        }
    }
