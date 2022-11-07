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