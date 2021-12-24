from django.db import models
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
# from django.contrib.auth.models import User

class Subscriber(models.Model):
    # user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    email = models.EmailField(unique=True)
    conf_num = models.CharField(max_length=15)
    confirmed = models.BooleanField(default=False)
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return self.email + " (" + ("not " if not self.confirmed else "") + "confirmed)"


class Newsletter(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subject = models.CharField(max_length=150)
    contents = models.FileField(upload_to='uploaded_newsletters/')

    def __str__(self):
        return self.subject + " " + self.created_at.strftime("%B %d, %Y")

    def send(self, request):
        contents = self.contents.read().decode('utf-8')
        subscribers = Subscriber.objects.filter(confirmed=True)
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        from_email = (settings.FROM_EMAIL, settings.SENDER_NAME)
        # print(from_email)
        for sub in subscribers:
            message = Mail(
                    from_email=from_email,
                    to_emails=sub.email,
                    subject=self.subject,
                    html_content=contents + (
                        # '<br><a href="{}/delete/?email={}&conf_num={}">Unsubscribe</a>.').format(
                            # request.build_absolute_uri(''),
                        '<br><a href="{}?email={}&conf_num={}">Unsubscribe</a>.').format(
                            request.build_absolute_uri('/delete/'),
                            sub.email,
                            sub.conf_num))
            sg.send(message)