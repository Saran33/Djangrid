from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='djangrid',
    packages=find_packages(include=['djangrid']),
    version='0.22',
    author='Saran Connolly',
    description='Django email marketing web app utilising the SendGrid API.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Saran33/djangrid",
    project_urls={
        "Bug Tracker": "https://github.com/Saran33/djangrid/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'django', 'sendgrid', 'sorl-thumbnail', 'django-tinymce', 'django-sendgrid-v5', 'django-extensions'
        'django-newsletter @ git+https://github.com/jazzband/django-newsletter.git#egg=django-newsletter',
        'django-advanced-filters @ git+https://github.com/Saran33/django-advanced-filters.git',
        'python-crontab',
    ],
    #package_dir={"": "src"},
    # packages=find_packages(where="djangrid"),
    python_requires="==3.9.9",
    setup_requires=['pytest-runner'],
    tests_require=['pytest==4.4.1'],
    test_suite='tests',
)
