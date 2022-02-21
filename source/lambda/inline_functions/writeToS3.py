import boto3
import cfnresponse

def lambda_handler(event, context):
    properties = event['ResourceProperties']
    apiId = properties['API_ID']
    bucket = properties['BucketName']
    try:
        s3 = boto3.resource('s3')
        data = """
// Replace the YOUR_API_ENDPOINT_URL with yours
// It should look something like this:
// https://example1a2s3d.execute-api.us-east-1.amazonaws.com/prod/reminders

var API_ENDPOINT = 'https://""" + apiId + """.execute-api.us-east-1.amazonaws.com/cradlepoint/routers';

// Setup divs that will be used to display interactive messages
var errorDiv = document.getElementById('error-message')
var successDiv = document.getElementById('success-message')
var resultsDiv = document.getElementById('results-message')

// Setup easy way to reference values of the input boxes
function deviceName() { return document.getElementById('deviceName').value }
function ipAddr() { return document.getElementById('ipAddr').value }
function macAddr() { return document.getElementById('macAddr').value }

function clearNotifications() {
    // Clear any exisiting notifications in the browser notifications divs
    errorDiv.textContent = '';
    resultsDiv.textContent = '';
    successDiv.textContent = '';
}

// Add listeners for each button that make the API request
document.getElementById('submitButton').addEventListener('click', function(e) {
    sendData(e);
});

function sendData (e) {
    // Prevent the page reloading and clear exisiting notifications
    e.preventDefault()
    clearNotifications()
    // Prepare the appropriate HTTP request to the API with fetch
    // create uses the root /prometheon endpoint and requires a JSON payload

    var myHeaders = new Headers();
    myHeaders.append("Content-Type", "application/json");

    var raw = JSON.stringify({
    "deviceName": deviceName(),
    "macAddr": macAddr(),
    "ipAddr": ipAddr()
    });

    var requestOptions = {
    method: 'POST',
    headers: myHeaders,
    body: raw,
    mode: 'cors',
    redirect: 'follow'
    };

    fetch(API_ENDPOINT, requestOptions)
    .then(response => response.json())
    .then(json => resultsDiv.textContent = json)
    .catch(err => resultsDiv.textContent = err); 
    };"""
    
        object = s3.Object(bucket, 'formlogic.js')
        result = object.put(Body=data)

    except Exception as e:
        print(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, {"Response": 'Failure'})
        return
    
    cfnresponse.send(event, context, cfnresponse.SUCCESS, {"Response": 'Success'})