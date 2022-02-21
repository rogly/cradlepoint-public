import boto3
import json
import re
import os

client = boto3.client('lambda')

def generateResponse(status, message):
    if(status == True):
        status = "Success"
        statusCode = 200
    else:
        status = "Error"
        statusCode = 400
    response = {
        "statusCode": statusCode,
        "headers": {"Access-Control-Allow-Origin":"*"},
        "body": json.dumps(message)
    }
    print(message)
    return response

def lambda_handler(event, context):
    data = json.loads(event['body'])

    # Validation Checks
    if not data['deviceName']:
        return generateResponse(False, "Please enter a device name")

    elif not re.match("[\w\d]{12}$", data['macAddr']):
        return generateResponse(False, "Please enter a valid MAC Address")

    elif not re.match("^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$" , data['ipAddr']):
        return generateResponse(False, "Please enter a valid IP Address")      

    # If no errors, call next function and return the result
    else:
        response = client.invoke(
            FunctionName = os.environ['DeployRouterArn'],
            InvocationType = 'RequestResponse',
            Payload = json.dumps(data)
        )
        responseFromChild = json.load(response['Payload'])
        return responseFromChild