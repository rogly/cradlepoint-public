import base64
import hashlib
import hmac
import json
import time

# Import boto3 for Secrets Manager
import boto3
from botocore.exceptions import ClientError

# Import requests for API Calls
import requests
from requests.api import request

# Import Smartsheet SDK
import smartsheet

# Initialize smartsheet global variables
column_map = {}

#Main Lambda Function
def lambda_handler(event, context):
    # Read in values from payload
    name = event['deviceName']
    mac = event['macAddr']
    ipAddress = event['ipAddr']
    
    # set variable for configuration wipe
    configReset = """
    {
        "configuration": [{}, []]
    }
"""
    # set variable for naming the device
    configName = """
    {
        "configuration": [
            {
                "system": {
                    "system_id": \"""" + name + """\"
                }
            },
            []
        ]
    }
"""

    ###############
    # Cradlepoint #
    ###############

    # Get Router ID
    url = 'https://www.cradlepointecm.com/api/v2/routers/?mac=' + mac + '&fields=id'
    response = CradlePointApi('GET', url)
    if(response.status_code != 200):
        logContent = "MAC Address:" + mac + " was not found"
        WriteLog(logContent)
        status = False
        message = logContent
        return generateResponse(status, message) 
        exit()
    
    else:
        parse = json.loads(response.text)
        parse = parse['data']
        parse = json.dumps(parse)
        parse = parse.replace("[","").replace("{","").replace("'","").replace("]","").replace("}","").replace("\"","").replace(" ","")
        parse = parse.split(":")
        routerID = parse[1]
        logContent = "Router ID: " + routerID + " was retrieved"
        WriteLog(logContent)

    # Get Device Serial
    url = 'https://www.cradlepointecm.com/api/v2/routers/?mac=' + mac + '&fields=serial_number'
    response = CradlePointApi('GET', url)
    if(response.status_code != 200):
        logContent = "MAC Address:" + mac + " was not found"
        WriteLog(logContent)
        status = False
        message = logContent
        return generateResponse(status, message) 
        exit()
    
    else:
        parse = json.loads(response.text)
        parse = parse['data']
        parse = json.dumps(parse)
        parse = parse.replace("[","").replace("{","").replace("'","").replace("]","").replace("}","").replace("\"","").replace(" ","")
        parse = parse.split(":")
        serialNumber = parse[1]
        logContent = "Serial Number: " + serialNumber + " was retrieved"
        WriteLog(logContent)

    # Get Configuration ID
    url = 'https://www.cradlepointecm.com/api/v2/configuration_managers/?router=' + routerID + '&fields=id'
    response = CradlePointApi('GET', url)
    if(response.status_code != 200):
        logContent = "Error Retrieving Config ID for " + name + " "
        WriteLog(logContent)
        status = False
        message = logContent
        return generateResponse(status, message)  
        exit()
    else:
        parse = json.loads(response.text)
        parse = parse['data']
        parse = json.dumps(parse)
        parse = parse.replace("[","").replace("{","").replace("'","").replace("]","").replace("}","").replace("\"","").replace(" ","")
        parse = parse.split(":")
        configID = parse[1]
        logContent = "Configuration ID: " + configID + " was retrieved for Router ID: " + routerID
        WriteLog(logContent)

    # Clear Configuration
    url = 'https://www.cradlepointecm.com/api/v2/configuration_managers/' + configID + '/?fields=version_number'
    response = CradlePointApi('PATCH', url, configReset)
    if(response.status_code != 202):
        logContent = "Error clearing configuration for " + name + " "
        WriteLog(logContent)
        status = False
        message = logContent
        return generateResponse(status, message)  
        exit()
    else:
        logContent = "Configuration ID: " + configID + " was cleared"
        WriteLog(logContent)

    # Set Device Name
    url = 'https://www.cradlepointecm.com/api/v2/configuration_managers/' + configID + '/?fields=version_number'
    response = CradlePointApi('PATCH', url, configName)
    if(response.status_code != 202):
        logContent = "Error naming device " + name + " "
        WriteLog(logContent)
        status = False
        message = logContent 
        return generateResponse(status, message) 
        exit()
    logContent = "RouterID: " + routerID + " was named " + name
    WriteLog(logContent)

    # Move To Private APN Group
    groupConfig = '{"group": "https://www.cradlepointecm.com/api/v2/groups/256223/"}'
    url = 'https://www.cradlepointecm.com/api/v2/routers/' + routerID + '/'
    response = CradlePointApi('PUT', url, groupConfig)
    if(response.status_code != 202):
        logContent = "Error moving device " + name + " to Private APN Group "
        WriteLog(logContent)
        status = False
        message = logContent 
        return generateResponse(status, message) 
        exit()
    else:
        logContent = "RouterID: " + routerID + " was moved to the Group: IBR900 (Private APN)"
        WriteLog(logContent)

    ################
    # LogicMonitor #
    ################

    # Add Device to LogicMonitor
    body = '{"name":"' + ipAddress + '","displayName":"' + name + '","hostGroupIds":340, "autoBalancedCollectorGroupId":4, "preferredCollectorId":0, "preferredCollectorGroupId":4}'
    response = LogicMonitorApi('POST', '/device/devices', '', body, 3)
    if(response.status_code != 200):
        logContent = "Error Adding " + name + " to LogicMonitor"
        WriteLog(logContent)
        status = False
        message = logContent 
        return generateResponse(status, message) 
        exit()            
    else:
        logContent = "Device with name: " + name + " and IP Address: " + ipAddress + " was added to LogicMonitor"
        WriteLog(logContent)
        status = True
        message = "Configuration of device with name: " + name + " and IP Address: " + ipAddress + " was sucessfully completed"
    
    ##############
    # SmartSheet #
    ##############

    # Initialize client. Uses the API token in the environment variable "SMARTSHEET_ACCESS_TOKEN"
    secret = json.loads(getSecret("lambda/smartsheet"))
    token = secret['Token']
    sheet_id = secret['SheetID']
    smart = smartsheet.Smartsheet(token)

    # Make sure we don't miss any error
    smart.errors_as_exceptions(True)

    # Load entire sheet
    sheet = smart.Sheets.get_sheet(sheet_id)

    print("Loaded " + str(len(sheet.rows)) + " rows from sheet: " + sheet.name)

    # Build column map for later reference - translates column names to column id
    for column in sheet.columns:
        column_map[column.title] = column.id

    # Accumulate cells needing updates here
    macsToUpdate = []
    namesToUpdate = []
    serialsToUpdate = []

    # Check each row for mac address updates
    for row in sheet.rows:
        macToUpdate = smartsheetEvaluateBuildUpdates(smart, row, ipAddress, "MAC Address", mac)
        if macToUpdate is not None:
            macsToUpdate.append(macToUpdate)

    # Check each row for name updates
    for row in sheet.rows:
        nameToUpdate = smartsheetEvaluateBuildUpdates(smart, row, ipAddress, "Name", name)
        if nameToUpdate is not None:
            namesToUpdate.append(nameToUpdate)

    # Check each row for serial updates
    for row in sheet.rows:
        serialToUpdate = smartsheetEvaluateBuildUpdates(smart, row, ipAddress, "Serial Number", serialNumber)
        if serialToUpdate is not None:
            serialsToUpdate.append(serialToUpdate)

    # Finally, write updated cells back to Smartsheet
    if macsToUpdate or namesToUpdate or serialsToUpdate:
        status = 200
        message = "Writing " + str(len(macsToUpdate) + len(namesToUpdate) + len(serialsToUpdate)) + " cell updates back to sheet: " + str(sheet.name)
        print(message)
        result = smart.Sheets.update_rows(sheet_id, macsToUpdate)
        result = smart.Sheets.update_rows(sheet_id, namesToUpdate)
        result = smart.Sheets.update_rows(sheet_id, serialsToUpdate)
    else:
        status = 200
        message = "No cell updates required"
        print(message)
    
    #Final Error Check
    if (status == 200):
        message = "Succesfully completed configuration of " + name
        return generateResponse(status, message)
    else:
        return generateResponse(status, message)

# Helper function to find cell in a row
def smartsheetCellByColumnName(row, column_name):
    column_id = column_map[column_name]
    return row.get_column(column_id)


def smartsheetEvaluateBuildUpdates(smart, source_row, match_address, update_column, update_value):
    # Find the cell and value we want to evaluate
    match_cell = smartsheetCellByColumnName(source_row, "IP Address")
    match_value = match_cell.display_value
    if match_value == match_address:
        update_cell = smartsheetCellByColumnName(source_row, update_column)
        if update_cell.display_value != update_value:  # Skip if already same value

            # Build new cell value
            new_cell = smart.models.Cell()
            new_cell.column_id = column_map[update_column]
            new_cell.value = update_value

            # Build the row to update
            new_row = smart.models.Row()
            new_row.id = source_row.id
            new_row.cells.append(new_cell)

            return new_row

    return None

# Function for making Cradlepoint API Calls            
def CradlePointApi(Verb,Uri,Body = ""):
    headers = json.loads(getSecret("lambda/cradlepoint"))
    if (Body):
        req = requests.request(Verb, Uri, headers=headers, data=Body)
    else:
        req = requests.request(Verb, Uri, headers=headers)
    return req

# Function for making LogicMonitor API Calls
def LogicMonitorApi(Verb, Path, Filter = "", Body = "", Version = ""):
    secret = json.loads(getSecret("lambda/logicmonitor"))
    AccessId = secret['AccessId']
    AccessKey = secret['AccessKey']
    Url = 'https://bkvcorp.logicmonitor.com/santaba/rest' + Path + Filter
    epoch = str(int(time.time() * 1000))
    requestVars = Verb + epoch + Body + Path
    hmac1 = hmac.new(AccessKey.encode(),msg=requestVars.encode(),digestmod=hashlib.sha256).hexdigest()
    signature = base64.b64encode(hmac1.encode())
    auth = 'LMv1 ' + AccessId + ':' + signature.decode() + ':' + epoch
    if(Version == 3):
        headers = {'Content-Type':'application/json','Authorization':auth, 'X-Version':'3'}
    else:
        headers = {'Content-Type':'application/json','Authorization':auth}
    if(Body):
        req = requests.request(Verb, Url, headers=headers, data=Body)
    else:
        req = requests.request(Verb, Url, headers=headers)
    return req

# Function for retrieving secrets from AWS Secrets Manager (Defaults to US-EAST-1 Region)
def getSecret(secret_name, region="us-east-1"):
    region_name = region
    
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    # Error Handling
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            raise e
    # If no errors, continue to retrieve secret
    else:
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            secret = base64.b64decode(get_secret_value_response['SecretBinary'])
        return secret

# Function for writing messages to CloudWatch
def WriteLog(Content):
    logLine = Content + "\n"
    print(logLine)

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