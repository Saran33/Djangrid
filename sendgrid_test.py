import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from dotenv import load_dotenv
# from dotenv import dotenv_values

load_dotenv('djangrid/sendgrid.env')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
# print (SENDGRID_API_KEY)

# sg_config = dotenv_values("djangrid/sendgrid.env")
# print(sg_config.keys())

message = Mail(
    from_email='support@zenstrabiohealth.com',
    to_emails='saranconnolly618@gmail.com',
    subject='Testing',
    html_content='<strong>Test message</strong>')
try:
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print(response.status_code)
    print(response.body)
    print(response.headers)
except Exception as e:
    print(e.message)