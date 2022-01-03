import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings

from dotenv import load_dotenv
# from dotenv import dotenv_values

# In terminal, to test locally, run: export DJANGO_SETTINGS_MODULE=djangrid.settings
# Or on heroku: heroku config:set DJANGO_SETTINGS_MODULE=mysite.settings --account <your account name> 

load_dotenv('djangrid/sendgrid.env')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
# print (SENDGRID_API_KEY)

# sg_config = dotenv_values("djangrid/sendgrid.env")
# print(sg_config.keys())

from_email=(settings.FROM_EMAIL, settings.SENDER_NAME)
print (from_email)
message = Mail(
    from_email=from_email,
    
    to_emails='testemail@gmail.com',
    subject='Testing',
    html_content='<strong>Test message</strong>')
try:
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    # response = sg.client.suppression.bounces.get()
    # response = sg.client._("suppression/bounces").get()
    print(response.status_code)
    print(response.body)
    print(response.headers)
except Exception as e:
    print(e.message)
