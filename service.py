# -*- coding: utf-8 -*-
import os
from py_s3_cache import Cache
from leafpy import Leaf
import time
import arrow
from boto3 import client as boto3_client
import boto3
import json
import requests

_MILES_PER_METER = 0.000621371

bucket = os.getenv('bucket')
prefix = os.getenv('prefix')
cacheprefix = prefix + 'cache'
cache = Cache(bucket,cacheprefix)

def handler(event, context):

    print event
    print context

    # PERIODIC UPDATE
    if event.get('detail-type') == 'Scheduled Event':
        print "doing periodic update (or async)"
        get_and_cache_leaf_data()
        return lambdaresponse('Update',"I am getting data from your Nissan Leaf.")

    # direct invoke to preheat asynchronously
    if event.get('detail-type') == 'preheat':
        print "preheat"
        leaf = getleaf()
        leaf.ACRemoteRequest()  # fire and forget
        return "did async preheat call"

    # direct the climate control to turn off
    if event.get('detail-type') == 'heatoff':
        print "heatoff"
        leaf = getleaf()
        leaf.ACRemoteOffRequest()  # fire and forget
        return "did async heatoff call"

    # direct the leaf to begin charging
    if event.get('detail-type') == 'startcharging':
        print "startcharging"
        leaf = getleaf()
        leaf.BatteryRemoteChargingRequest()  # fire and forget
        return "did async startcharging call"

    # Preheat
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'PreheatIntent':
        msg = {'detail-type':'preheat'}
        launch_lambda(context.function_name, msg)
        return lambdaresponse('Update',"Sure, I'm cranking up the heat in your Nissan Leaf.")

    # CoolAC
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'CoolingIntent':
        msg = {'detail-type':'preheat'}
        launch_lambda(context.function_name, msg)
        return lambdaresponse('Update',"Yeah!  I'm turning on the AC.  Prepare to be mega chilled.")

    # HeatOff
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'HeatOffIntent':
        msg = {'detail-type':'heatoff'}
        launch_lambda(context.function_name, msg)
        return lambdaresponse('Update',"Okay okay.  I'm turning off the heat.")

    # AC Off
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'CoolOffIntent':
        msg = {'detail-type':'heatoff'}
        launch_lambda(context.function_name, msg)
        return lambdaresponse('Update',"I'm turning off the Air Conditioner.")

    # Start Charging
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'StartChargingIntent':
        msg = {'detail-type':'startcharging'}
        launch_lambda(context.function_name, msg)
        return lambdaresponse('Update',"Okay I'll start charging your leaf.")

    # Please update
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'UpdateIntent':
        msg = {'detail-type':'Scheduled Event'}
        launch_lambda(context.function_name, msg)
        return lambdaresponse('Update',"I am getting data from your Nissan Leaf.  It will take about 30 seconds.")
        
    # Where is my nissan leaf
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'LocationIntent':
        data = cache.get('leafdata')
        lat = data.get('lat')
        lng = data.get('lng')
        url = "https://maps.googleapis.com/maps/api/geocode/json?latlng=%s,%s" % (lat,lng)
        print url
        r = requests.get(url)
        print r.text
        location_str = r.json()['results'][0]['formatted_address']
        return lambdaresponse('Location',"Your Leaf is located at "+location_str)

    # How much battery do I have left
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'ChargeIntent':
        data = cache.get('leafdata')
        response_str = 'Your leaf has %s percent battery remaining.' % data.get('percent')
        return lambdaresponse('Battery Remaining',response_str)

    # Is it plugged in
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'ConnectedIntent':
        data = cache.get('leafdata')
        if data.get('connected'):
            return lambdaresponse('Plugged in','Your leaf is currently plugged in.')
        else:
            return lambdaresponse('Not Plugged in','Your leaf is not plugged in.')
        
    # How far can I drive
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'RangeIntent':
        data = cache.get('leafdata')
        response_str = 'Your leaf can go %s miles on its current charge of %s percent battery capacity.' % (data.get('distance'), data.get('percent'))
        return lambdaresponse('Driving Range',response_str)

    # is it charging
    if event.get('request').get('type') == 'IntentRequest' and event['request']['intent']['name'] == 'ChargingIntent':
        data = cache.get('leafdata')
        if data.get('charging'):
            return lambdaresponse('Charging','Your leaf is currently charging.')
        else:
            return lambdaresponse('Not Charging','Your leaf is not charging.')



def get_and_cache_leaf_data():
    leaf = getleaf()
    response = leaf.BatteryStatusCheckRequest()   # Send an async battery status request
    location_response = leaf.MyCarFinderRequest() # Send an async car location request

    timeout_start = time.time()
    # wait maximum of 2 minutes for battery status async request to finish
    while time.time() < timeout_start + 120:
        time.sleep(5)
        r = leaf.BatteryStatusCheckResultRequest(resultKey=response['resultKey'])
        if r.get('responseFlag') == '1':
            break

    # wait for position status async request to finish
    while True:
        time.sleep(5)
        r = leaf.MyCarFinderResultRequest(resultKey=location_response['resultKey'])
        if r.get('responseFlag') == '1':
            break

    response = leaf.BatteryStatusRecordsRequest()

    data = {
        'charging': response['BatteryStatusRecords']['BatteryStatus']['BatteryChargingStatus'] != 'NOT_CHARGING',
        'connected': response['BatteryStatusRecords']['PluginState'] == 'CONNECTED',
        'percent': int(response['BatteryStatusRecords']['BatteryStatus']['SOC']['Value']),
        'distance': int(( int(response['BatteryStatusRecords']['CruisingRangeAcOn']) ) * _MILES_PER_METER),
        'timestamp': str(arrow.utcnow())
    }

    # Now get leaf location (this is a pretty quick request)
    response = leaf.MyCarFinderLatLng()
    data['lat'] = float(response.get('lat'))
    data['lng'] = float(response.get('lng'))

    cache.set('leafdata',data)

    # now additionally save the data in s3 as a record for future analysis with AWS Athena
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket,prefix + '/data/' + str(data['timestamp'].replace('T',' ')) + '.txt')
    datastr = data['timestamp'].replace('T',' ') + ',' + str(data['percent']) + ',' + str(data['distance']) + ',' + str(data['charging'])+ ',' + str(data['connected'])
    datastr = datastr + ',' + str(data['lat']) + ',' + str(data['lng'])
    obj.put(Body=datastr)

def getleaf():
    username = os.getenv('username')
    password = os.getenv('password')
    leaf = cache.get('leaf')
    if not leaf:
        leaf = Leaf(username, password)

    # Make sure the leaf custom_sessionid is valid
    try:
        leaf.BatteryStatusRecordsRequest()
    except:
        leaf = Leaf(username, password)

    cache.set('leaf',leaf)
    return leaf

def launch_lambda(function_name, msg):
    """
    Fire and forget invoking this lambda so we can respond to the user without waiting.
    """
    # func_name: context.function_name
    lambda_client = boto3_client('lambda','us-east-1')
    invoke_response = lambda_client.invoke(FunctionName=function_name,InvocationType='Event',Payload=json.dumps(msg))

def lambdaresponse(title, text):
    return {
      "version": "1.0",
      "response": {
        "outputSpeech": {
          "type": "PlainText",
          "text": text
        },
        "card": {
          "content": text,
          "title": title,
          "type": "Simple"
        }
      },
      "sessionAttributes": {}
    }
