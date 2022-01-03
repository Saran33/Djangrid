from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives

# To test sendgrid v5.
# In terminal, run: export DJANGO_SETTINGS_MODULE=djangrid.settings

# send_mail(
#     'Testing',
#     '<strong>Test message</strong>',
#     settings.FROM_EMAIL,
#     ['testemail@gmail.com'],
#     fail_silently=False,
# )

subject = 'Testing'
text = '<strong>Test message</strong>'
from_email = settings.MAIL_FROM
to = 'Your Name <testemail@gmail.com>'

message = EmailMultiAlternatives(
    subject, text,
    from_email=from_email,
    to=[to]
)

message.send(fail_silently=False)