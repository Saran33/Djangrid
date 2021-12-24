conda activate zenstra
source djangridenv/bin/activate
cd djangrid

https://sendgrid.com/
https://github.com/sendgrid/sendgrid-python
https://github.com/sendgrid/sendgrid-python/blob/main/use_cases/kitchen_sink.md

https://www.twilio.com/blog/build-email-newsletter-django-twilio-sendgrid

https://www.codingforentrepreneurs.com/blog/sendgrid-email-settings-for-django/
https://docs.sendgrid.com/for-developers/sending-email/django
https://github.com/sklarsa/django-sendgrid-v5
https://simpleit.rocks/python/django/adding-email-to-django-the-easiest-way/
https://github.com/philipkiely/twilio_email_newsletter_code
https://github.com/jazzband/django-newsletter



# Create Environment
Create either a conda env or venv or virtualenv
`python --version`
### Create Env
`conda create --name djangridenv python=3.10`
`conda activate djangridenv`
#### Venv
`python3 -m venv djangridenv`
### Virtulenv
`pip install virtualenv`
1. Create virtualenv:
`virtualenv djangridenv --python=python3.10`
2. Launch venv:
windows:
`./djangridenv/scripts/activate`
unix:
`source djangridenv/bin/activate`
Exit venv:
`deactivate`
Delete venv:
`rm -rf djangridenv`
Remake from requitements.txt:
`pip install -r requirements.txt`

# Requirements
`pip install django sendgrid`
`pip install -e git://github.com/jazzband/django-newsletter.git#egg=django-newsletter`

# SendGrid API Setup
- Create account and API key.
- `pip install python-dotenv` https://github.com/theskumar/python-dotenv
```zsh
echo "export SENDGRID_API_KEY='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'" > sendgrid.env
echo "sendgrid.env" >> .gitignore
source ./sendgrid.env
```


# Django Setup
`django-admin startproject djangrid`
`cd djangrid`
`python manage.py startapp djangridApp`
`python manage.py makemigrations`
`python manage.py migrate`
1. Add `djangridApp` to installed apps in settings.py, as well as FROM_EMAIL and SENDGRID_API_KEY.
2. `python manage.py createsuperuser`
3. Add subscribers model
```zsh
python manage.py makemigrations
python manage.py migrate
```
4. Register the Subscriber model in admin.py
5. `python manage.py runserver`
- http://127.0.0.1:8000/admin/
6. Add a route for adding a new subscriber in djangrid/urls.py
7. Add a view to djangridApp/views.py
7. Add a view to djangridApp/views.py
8. Create djangridApp/forms.py
9. Create a signup page with Bootstrap in djangridApp/templates/index.html
10. Add the confirmation view in views.py NEED TO CHANGE THIS TO A TOKEN!
11. Add the confirmation url to urlpatterns in djangrid/urls.py
12. test on http://127.0.0.1:8000/subscribe
13. Delete a subscriber: views.py and add it to urlpatterns in djangrid/urls.py
14. Sending Newsletters: 
- Create djangrid/uploaded_newsletters dir then add the dir as a MEDIA_URL in settings.py
- Create a Newsletter model.
```zsh
python manage.py makemigrations
python manage.py migrate
```
- Register the model in DjangridApp/admin.py
15. Use the admin dashboard to upload HTML formatted newsletters (dashboard supports file uploads)
`python manage.py runserver`
http://127.0.0.1:8000/admin/
- e.g. `<p>Test Email</p><p>You are reading my email newsletter, and this is one of those newsletters!</p>`  as test_email.html
16. Add a send function to the Newsletter model.
17. Invoke this method as an admin action in DjangridApp/admin.py, to make it availabe in the admin panel.
- images/Send_Newsletter_django_admin_action.png
