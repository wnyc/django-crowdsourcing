**********
Developers
**********

Intro
=====

The example application is a great place to start. You can also review the producer's documentation as that explains what all the fields are for and how to use them. Finally, the source itself is a good place to look.

Setting Up the Example Application
==================================

crowdsourcing_requirements.txt is a pip requirements file that describes the basic requirements for crowdsourcing. example_app/example_app_requirements.txt has requirements necessary for the example app. You can install these requirements through steps like these::

  $ easy_install pip
  $ pip install mercurial
  $ hg clone https://django-crowdsourcing.googlecode.com/hg/ django-crowdsourcing
  $ cd django-crowdsourcing
  django-crowdsourcing $ pip install -r crowdsourcing_requirements.txt
  django-crowdsourcing $ pip install -r example_app/example_app_requirements.txt

  Take whatever steps you need to install a database. Put the appropriate
  settings in example_app/local_settings.py Perhaps your local_settings.py will
  look something like this:

  DATABASE_ENGINE = 'postgresql_psycopg2'
  DATABASE_HOST = '127.0.0.1'
  DATABASE_PORT = ''
  DATABASE_NAME = 'my_database'
  DATABASE_USER = 'me'
  DATABASE_PASSWORD = 'my_password'

  django-crowdsourcing $ cd example_app
  django-crowdsourcing/example_app $ ./manage.py syncdb
  django-crowdsourcing/example_app $ ./manage.py runserver

Pre-Report Filter
=================

Crowdsourcing does not dictate what ratings or comments system you use. However, a common use case is to sort submissions descending by their rating. Crowdsourcing provides a hook so you can arbitrarily modify the query object that pulls back submissions just before they display to accomplish just such a task.

Start by creating a function with this signature. To accomplish the use case above, you'll also include some code like the following::

  def my_pre_report_filter(submissions, report, request):
      default_sort = "Rating" if report.sort_by_rating else ""
      if "Rating" == request.GET.get("sort", default_sort):
          # Sort by rating here.
          submissions = submissions.order_by(...)
      return submissions

Next, create this setting to let crowdsourcing know where to find your hook::

  CROWDSOURCING_PRE_REPORT = 'my.app_path.my_pre_report_filter'

Settings
========

You can see all the possible configuration settings, and in some cases more detailed notes in crowdsourcing/settings.py.

**CROWDSOURCING_MODERATE_SUBMISSIONS**

This sets the default "Moderate submissions" value of surveys.

**CROWDSOURCING_IMAGE_UPLOAD_PATTERN**

Relative to your MEDIA directory.

**CROWDSOURCING_FLICKR_API_KEY**

If you interface with Flickr for photo uploads you'll need to set this property. In fact there are several authentication properties you'll need to set including **CROWDSOURCING_FLICKR_API_SECRET**, **CROWDSOURCING_FLICKR_TOKEN**, and **CROWDSOURCING_FLICKR_FROB**. See crowdsourcing/settings.py for a detail explanation of how I used the Django shell to retrieve the frob and token.

**CROWDSOURCING_FLICKR_LIVE**

Are Flickr photos live by default?

**CROWDSOURCING_FLICKR_TOKENCACHE_PATH**

Your application will need permission to this file path.

**CROWDSOURCING_PRE_REPORT**

This path to a function is discussed in detail under "Pre-Report Filter."

**CROWDSOURCING_SURVEY_EMAIL_FROM**

You can set up individual surveys to e-mail a list of people when users create new submissions. This setting says where that e-mail will come from. 

**CROWDSOURCING_SURVEY_ADMIN_SITE**

This site is for the notification emails that crowdsourcing sends when a user enters a survey. The default is the site the user entered the survey on.

**CROWDSOURCING_OEMBED_EXPAND**

You can set a custom ``def oembed_expand(url, **opts)`` which takes the url to a video and returns html embed code. Use the form ``path.to.my_function``

**CROWDSOURCING_LOGIN_VIEW**

What URL should crowdsourcing redirect users to if they try to enter a survey that requires a login?

**CROWDSOURCING_VIDEO_URL_PATTERNS**

youtube has a lot of characters in their ids now so use ``[^&]``. youtube also likes to add additional query arguments, so no trailing ``$``. If you have oembed installed, crowdsourcing uses the oembed configuration and ignores this.

**CROWDSOURCING_GOOGLE_MAPS_API_KEY**

crowdsourcing.templatetags.crowdsourcing.google_map uses this setting.

**CROWDSOURCING_EXTRA_THUMBNAILS**

A dictionary of extra thumbnails for Submission.image_answer, which is a sorl ImageWithThumbnailsField. For example, ``{'slideshow': {'size': (620, 350)}}``
