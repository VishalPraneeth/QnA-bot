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


def check_item_exists(region_name: str, table_name: str, needle: str) -> bool:
    """
    Check if the given dynamodb item exists.
    Query with limit of 1 is performed.
    """
    resp = { 'item_exists':False }
    if not needle: needle = 'auto'
    client = boto3.client('dynamodb', region_name = region_name)
    try:
        # resp['Items'] = table.query( KeyConditionExpression = Key('search_query').eq( str(needle).lower() ) )
        r1 = client.query(TableName = table_name,
                            KeyConditionExpression='search_query = :var1',
                            ExpressionAttributeValues={
                                ":var1":{"S": needle.lower()}
                            },
                            ProjectionExpression = "search_query, #ui, utterances",
                            ExpressionAttributeNames = {'#ui': 'user_ids'}
                            )
        if ( r1.get('Count') == 1 or r1.get('Count')>1 ) and len(r1.get('Items')) == 1:
            resp['Items'] = r1.get('Items')
            resp['item_exists'] =  True
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")
    return resp


async def create_ddb_item(region_name: str, table_name: str, item: dict):
    """
    Create DDB Item
    """
    dynamodb = boto3.resource('dynamodb', region_name = region_name)
    table = dynamodb.Table(table_name)
    try:
        response = table.put_item(
           Item={
                'search_query': str( item.get('search_query') ),
                'search_count': 1,
                'created_on' : str(datetime.datetime.now()),
                'user_ids': [item.get('user_id')],
                'utterances': [item.get('utterance')]
            }
        )
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")


async def update_ddb_item(region_name: str, table_name: str, item: dict):
    """
    Helper function to Insert / Update item in table
    Add email_sent attribute and set to true
    REMOVE next_lead attribute
    """
    dynamodb = boto3.resource('dynamodb', region_name = region_name)
    table = dynamodb.Table(table_name)
    try:
        u_ex = f'SET search_count= search_count + :incr, last_searched= :var2'
        ex_val = {
                    ':incr' : 1,
                    ':var2' :str(datetime.datetime.now())
                }
        if item.get('user_id'):
            u_ex+=f', user_ids = list_append(user_ids, :var3)'
            ex_val[':var3'] = [str( item.get('user_id') ) ]
        if item.get('utterance'):
            u_ex+=f', utterances = list_append(utterances, :var4)'
            ex_val[':var4'] = [str( item.get('utterance') ) ]
        response = table.update_item(TableName = table_name,
                                        Key={'search_query':str( item.get('search_query') ) },
                                        # UpdateExpression='SET email_sent= :var1 REMOVE next_lead',
                                        UpdateExpression = u_ex,
                                        ExpressionAttributeValues = ex_val
                                    )
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")


def build_response_card_slack(options):
    """
    Build a responseCard with a title, subtitle, and an optional set of options which should be displayed as buttons.
    """
    cards = []
    if options is not None:

        # imageUrl = options[0].get('thumbnails')
        for i in range(min(5, len(options))):
            t = {}
            t['title'] = f"{options[i].get('title')[:75]}..."
            t['subTitle'] = f"*ViewCount*: *`{options[i].get('view_count')}`* *Popularity*: *`{options[i].get('popularity')}`*"
            t['attachmentLinkUrl'] = f"https://www.youtube.com/watch?v={options[i].get('vid_id')}"
            t['imageUrl'] = options[i].get('thumbnails')
            cards.append(t)
    return {
        'contentType': 'application/vnd.amazonaws.card.generic',
        'version': 1,
        'genericAttachments': cards
        }


def close_w_card(session_attributes, fulfillment_state, message, options):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message,
            "responseCard": build_response_card_slack(options)
        }
    }
    logger.debug( json.dumps(response, indent=4, sort_keys=True) )
    return response


def close(session_attributes, fulfillment_state, message_content):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message_content
        }
    }
    return response