from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import Profile
from .forms import ProfileForm
import random
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.utils.timezone import now
from .utils import make_activation_code

# def random_digits():
#     return "%0.12d" % random.randint(0, 999999999999)

@csrf_exempt
def subscribe(request):
    if request.method == 'POST':
        sub = Profile.objects.get(email=request.POST['email'])
        if sub:
            if not sub.unsubscribed:
                sub.unsubscribed = False
                sub.conf_num = make_activation_code()
                sub.save()
                message = send_conf_email(request, sub.email, sub.conf_num)
                message = send_conf_email(request, sub.email, sub.conf_num)
                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                response = sg.send(message)
                return render(request, 'index.html', {'email': sub.email, 'action': 'added', 'form': ProfileForm()})
        else:
            sub = Profile(email=request.POST['email'], conf_num=make_activation_code())
            sub.save()

            message = send_conf_email(request, sub.email, sub.conf_num)
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)

            return render(request, 'index.html', {'email': sub.email, 'action': 'added', 'form': ProfileForm()})
    else:
        return render(request, 'index.html', {'form': ProfileForm()})

def send_conf_email(request, email, conf_num):
    message = Mail(
                from_email=settings.MAIL_FROM,
                to_emails=email,
                subject='Newsletter Confirmation',
                html_content='Thank you for signing up to our newsletter! \
                    Please complete the process by \
                    <a href="{}?email={}&conf_num={}"> clicking here to \
                    confirm your registration</a>.'.format((request.build_absolute_uri('/newsletter/confirm/').replace('/subscribe', '')),  # request.build_absolute_uri('/confirm/')
                                                        email,
                                                        conf_num))
    return message

def confirm(request):
    sub = Profile.objects.get(email=request.GET['email'])
    if sub.conf_num == request.GET['conf_num']:
        sub.confirmed = True
        sub.save()
        return render(request, 'index.html', {'email': sub.email, 'action': 'confirmed'})
    else:
        return render(request, 'index.html', {'email': sub.email, 'action': 'denied'})


def delete(request):
    sub = Profile.objects.get(email=request.GET['email'])
    if sub.conf_num == request.GET['conf_num']:
        # sub.delete()
        sub.unsubscribed = True
        sub.unsubscribe_date = now
        return render(request, 'index.html', {'email': sub.email, 'action': 'unsubscribed'})
    else:
        return render(request, 'index.html', {'email': sub.email, 'action': 'denied'})