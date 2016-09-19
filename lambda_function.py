###
#   Name: CFN-Lambda-TemplateGenerator
#   Purpose: This script takes in a harness of variables and the location of an 
#       Jinja2 Template in S3 and uses it to generate a file and file and upload
#       it to S3. For exmaple, it can generate an iterated child template.
#   Authour: Taylor Bertie (nightkhaos@gmail.com)
#   Last Updated: 2016-09-13
#   Version: 1.0.1
#   Example Input:
#        {
#          "StackId": "arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid",
#          "ResponseURL": "http://pre-signed-S3-url-for-response",
#          "ResourceProperties": {
#             "TemplateS3Bucket" : "bucket",
#             "TemplateS3Key" : "templatepath/template.j2",
#             "HarnessLiterals": {
#                "ReplaceMe" : "Test"
#             },
#             "CommaLists" : {
#                "ThisIsAList" : "value1,value2,value3"
#             },
#             "S3Bucket" : "bucket",
#             "S3KeyPrefix" : "templatepath/",
#             "S3Suffix" : "json"
#          },
#          "RequestType": "Create",
#          "ResourceType": "Custom::TestResource",
#          "RequestId": "unique id for this create request",
#          "LogicalResourceId": "MyTestResource"
#          }

from cfnlambda import handler_decorator, RequestType
from jinja2 import Environment as j2Env, FileSystemLoader as j2FileLoader
import boto3 as awsapi
import logging


@handler_decorator(delete_logs=False)
def lambda_handler(event, context):
    s3 = awsapi.client('s3')
    logger = logging.getLogger(__name__)
    logging.getLogger().setLevel(logging.INFO)
    
    # Verify variables and put in useful variable names
    # Harness Literals may not exist, and must be a dict
    if 'HarnessLiterals' in event['ResourceProperties']:
        Harness = event['ResourceProperties']['HarnessLiterals']
        if type(Harness) != dict:
            logger.error('The Property "HarnessLiterals" was not a dictionary.')
            return False
    else:
        Harness = {}
    
    # S3Bucket must exist
    if 'S3Bucket' in event['ResourceProperties']:
        S3Bucket = event['ResourceProperties']['S3Bucket']
    else:
        logger.error('The Property "S3Bucket" must exist and point to an S3 Bucket this function has DeleteObject, PutObject and' + \
                'GetObject permissions for at the key prefix provided by S3KeyPrefix.')
        return False
    
    # S3KeyPrefix may not exist
    if 'S3KeyPrefix' in event['ResourceProperties']:
        S3KeyPrefix = event['ResourceProperties']['S3KeyPrefix']
    else:
        S3KeyPrefix = ''

    # S3Suffix may not exist This will fail softly to no extension if no valid suffix is provided.
    S3Suffix = ('.' + event['ResourceProperties']['S3Suffix']) if 'S3Suffix' in event['ResourceProperties'] else ''

    # TemplateS3Bucket must exist, and must be a string and TemplateS3Key must exist
    if 'TemplateS3Bucket' not in event['ResourceProperties'] or 'TemplateS3Key' not in event['ResourceProperties']:
        logger.error('The properties "TemplateS3Bucket" and "TemplateS3Key" were not omitted or misspelled. These values must point' + \
            'to an object that this function has GetObject permissions for.')
        return False
    TemplateS3Bucket = event['ResourceProperties']['TemplateS3Bucket']
    TemplateS3Key = event['ResourceProperties']['TemplateS3Key']

    # CommaLists may exist, and must be a dict
    # Add the CommaLists to Harness as lists
    if 'CommaLists' in event ['ResourceProperties']:
        if type(event['ResourceProperties']['CommaLists']) != dict:
                logger.error('The Property "CommaList" was not a dictionary.')
                return False
        # Add the CommaLists keys to Harness
        for key in event['ResourceProperties']['CommaLists']:
            if key in Harness: 
                logger.warn("The property \"%s\" exists in HarnessLiterals. CommaLists values will override HarnessLiterals." % key)
            Harness[key] = event['ResourceProperties']['CommaLists'][key].split(',')
    else:
        logger.warn('No CommaLists dictionary detected. If you are not iterating over value why do you need this function?')
    
    # The S3 Resourse Name by convention is bucket: ${S3Bucket}; key: ${S3KeyPrefix}${LogicalResourceId}-${!StackGUID}.${S3Suffix}
    # Where !StackGUID is the guid at the end of the stack ID.
    S3Guid = event['StackId'].rsplit('/')[-1]
    S3FileName = S3KeyPrefix + event['LogicalResourceId'] + '-' + S3Guid + S3Suffix

    # If the request type is "Delete" we only need to delete the S3 Object if it exists
    if event['RequestType'] == RequestType.DELETE:
        logger.info("Detected stack deletion, deleting object s3://" + S3Bucket + "/" + S3FileName)
        response = s3.delete_object(Bucket=S3Bucket,Key=S3FileName)
        return response
   
    logger.info("Attempting to open the provided template object at s3://" + TemplateS3Bucket + "/" + TemplateS3Key)
    with open("/tmp/template.j2", "wb") as f:
        s3.download_fileobj(TemplateS3Bucket, TemplateS3Key, f)
        f.close()

    # Produce the template
    env = j2Env(loader=j2FileLoader('/tmp'))
    template = env.get_template('template.j2')
    
    # Attempt to upload the template
    logger.info("Applying harness to template object to create result file")
    with open("/tmp/result.txt","wb") as f:
        f.write(template.render(Harness))
        f.close()
    
    logger.info("Attempting to upload result file to s3://" + S3Bucket + "/" + S3FileName)
    with open("/tmp/result.txt","rb") as f:
        s3.upload_fileobj(f, S3Bucket, S3FileName)
        f.close()

    # Return the Template URL
    logger.info("Returning result file path under TemplateS3Url Attribute")
    returnValue = {}
    
    #returnValue['TemplateS3Url'] = 'https://s3-' + S3BucketLocation + '.amazonaws.com/' + S3Bucket + '/' + S3FileName
    returnValue['TemplateS3Url'] = 'https://' + S3Bucket + '.s3.amazonaws.com/' + S3FileName
    return returnValue 

