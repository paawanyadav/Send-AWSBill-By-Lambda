import boto3, json, os
from datetime import date
from datetime import timedelta 
import smtplib  
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
organizations_client = boto3.client('organizations')

client = boto3.client('ce')
billing_client = boto3.client('ce')

today = date.today()
year = str(today.year)
month = today.strftime("%m")

TempReci = []


def lambda_handler(event,context):
    CurrentAccountid = boto3.client('sts').get_caller_identity().get('Account')
    CurrentAccountname =   boto3.client('organizations').describe_account(AccountId=CurrentAccountid).get('Account').get('Name')
   
    


    CurrentAccountname2 =  boto3.client('organizations').list_accounts()
#print(CurrentAccountname2['Accounts'][0]["Email"])
####################INPUT VARIABLES####################### 

# Replace sender@example.com with your "From" address. 
    # This address must be verified.
    SENDER = 'senders mail id' 
    SENDERNAME = 'Senders name'
    
    for i in range(len(CurrentAccountname2['Accounts'])):
        TempReci.append(CurrentAccountname2['Accounts'][i]["Email"])
    # Replace recipient@example.com with a "To" address. If your account 
    # is still in the sandbox, this address must be verified.
    #you can give multiple email id with comma seperated manner
    temp=(', '.join(TempReci))
    RECIPIENT  = temp
    
    # Replace smtp_username with your Amazon SES SMTP user name.
    USERNAME_SMTP = "write your SMTP username"
    
    # Replace smtp_password with your Amazon SES SMTP password.
    PASSWORD_SMTP = "write your SMTP password"
   
    # If you're using Amazon SES in an AWS Region other than US West (Oregon), 
    # replace email-smtp.us-west-2.amazonaws.com with the Amazon SES SMTP  
    # endpoint in the appropriate region.
    HOST = "email-smtp.us-east-1.amazonaws.com"
    PORT = 587
    


#  str_thresholdCost=str(thresholdCost)
    str_today = str(today)  

    startdate = year + '-' + month + '-01'

  # connecting to cost explorer to get monthly cost of the child accounts
    childAccountDetails = organizations_client.list_accounts(
        )
    data = []

    for account in childAccountDetails['Accounts'] :
        data.append([account['Name'],account['Id'],account['Email']])
    
    
    result = []
    
    for name,id,EMAIL in data :
        response = billing_client.get_cost_and_usage(
            TimePeriod={
                'Start': startdate,
                'End': str_today, },
                Granularity='MONTHLY',
                Metrics=[ 'UnblendedCost',],
                Filter={
                    'Dimensions': {
                        'Key': 'LINKED_ACCOUNT',
                        'Values': [id,
                        ]
                        }
                        }
                        
                          )
        tags = organizations_client.list_tags_for_resource(
        ResourceId=id
        )
        for tag in tags['Tags']:
            if tag['Key'] == 'Cost Center':
                cost_center = (tag['Value'])
            
        for r in response['ResultsByTime']:
            bill_amount=round(float((r['Total']['UnblendedCost']['Amount'])))
            result.append((name,EMAIL,'cost_center',id,bill_amount))
            
                

    ses_payload = """<html>
                <head>
                    <style>
                    table {
                    font-family: arial, sans-serif;
                    border-collapse: collapse;
                    width: 100%;
                    }
                    
                    td, th {
                    border: 1px solid #dddddd;
                    text-align: left;
                    padding: 8px;
                    }
                    
                    tr:nth-child(even) {
                    background-color: #dddddd;
                    }
                    </style>
                    </head>
                <body>
                    <table>
                        <tr>
                            <th>Account Name</th>
                            <th>Root Email</th>
                            <th>Cost Center</th>
                            <th>Account ID</th>
                            <th>Bill in USD</th>
                        </tr>
                    """
    for name,EMAIL,cost_center,id,bill_amount in result :
        ses_payload +="""<tr>
        <td style = 'width:30%'>""" + str(name) + """</td>
        <td style = 'width:25%'>""" + str(EMAIL) + """</td>
        <td style = 'width:20%'>""" + str(cost_center) + """</td>
        <td style = 'width:15%'>""" + str(id) + """</td>
        <td style = 'width:15%'>""" + '$' + str(bill_amount) + """</td>
        </tr>
        """
        ses_payload +="""</table>
                    </body>
                </html>
                """    

    
    # (Optional) the name of a configuration set to use for this message.
    # If you comment out this line, you also need to remove or comment out
    # the "X-SES-CONFIGURATION-SET:" header below.
#    CONFIGURATION_SET = "ConfigSet"
    

    # The subject line of the email.
    SUBJECT = 'Bill details for Linked AWS Accounts under ' + CurrentAccountname + ' (' + CurrentAccountid + ') from ' + str(startdate) + ' to ' + str(today)
    
    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = ("Billing alert for internal child accounts\r\n"
                 "This email was sent through the Amazon SES SMTP "
                 "This contains internal child accounts billing details, which are only visible for email clients."
                )
    
    # The HTML body of the email.
    BODY_HTML = ses_payload
    
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = SUBJECT
    msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
    msg['To'] = (', ').join(RECIPIENT.split(','))
    # Comment or delete the next line if you are not using a configuration set
#    msg.add_header('X-SES-CONFIGURATION-SET',CONFIGURATION_SET)
    
    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(BODY_TEXT, 'plain')
    part2 = MIMEText(BODY_HTML, 'html')
    
    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)
    
    # Try to send the message.
    try:  
        server = smtplib.SMTP(HOST, PORT)
        server.ehlo()
        server.starttls()
        #stmplib docs recommend calling ehlo() before & after starttls()
        server.ehlo()
        server.login(USERNAME_SMTP, PASSWORD_SMTP)
        server.send_message(msg)
        server.close()
    # Display an error message if something goes wrong.
    except Exception as e:
        print ("Error: ", e)
    else:
        print ("Email sent!")
