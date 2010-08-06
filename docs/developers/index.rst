**********
Developers
**********

This documentation is meant for the technical people who will install crowdsourcing, tailor it for your website, and keep it running.

The example application is a great place to start. You can also review the producer's documentation as that explains what all the fields are for and how to use them.

If you want to go directly to the source, these files are particularly important.

* crowdsourcing/models.py
* crowdsourcing/urls.py
* crowdsourcing/views.py
* crowdsourcing/templatetags/crowdsourcing.py

Installation
============


Prerequisites are:

 * Django itself, of course -- 1.1 or better.
 * `PIL`_
 * `django-positions`_
 * `sorl-thumbnail`_
 * `flickrapi`_ (optional)

Django-crowdsourcing itself can be installed with `pip`_::

  $ # probably in a virtualenv ...
  $ pip install django-crowdsourcing 

.. _`PIL`: http://pythonware.com/products/pil/
.. _`django-positions`: http://github.com/jpwatts/django-positions 
.. _`sorl-thumbnail`: http://code.google.com/p/sorl-thumbnail/
.. _`pip`: http://pip.openplans.org/
.. _`flickrapi`: http://stuvel.eu/projects/flickrapi


Setting Up the Example Application
==================================

The example application is a great resource for developers. It lays out a simple example of how to get all the gritty details working together. Perhaps even more importantly it contains a lot of very useful Javascript which you will probably want to include in your application.

crowdsourcing_requirements.txt is a pip requirements file that describes the basic requirements for crowdsourcing. example_app/example_app_requirements.txt has requirements necessary for the example app. You can install these requirements and the example app through steps like these::

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

A Note on Nomenclature
======================

Crowdsourcing uses the terms "field" and "question" interchangeably. This is because in some contexts it makes sense to refer to the questions of a survey, while in other contexts you may want to think in terms of fields of a survey object.

Templates
=========

The example application is a great place to look for guidance on how to set up your templates.

crowdsourcing.templatetags.crowdsourcing has a lot of useful templatetags. Each templatetag is a simple tag which makes it easy to use with both the Django and Mako templating systems. For example, in Django::

  {% load crowdsourcing %}
  {% yahoo_api %}

In Mako::

  <% from crowdsourcing.templatetags import crowdsourcing %>
  ${crowdsourcing.yahoo_api()}

Create a crowdsourcing folder in your templates directory. You'll need the following templates in that folder.

**survey_detail.html**

This template displays the survey entry form. The context is

* *survey*
* *forms*: One Django form per question. If the user can't enter the survey, forms will be an empty tuple.
* *entered*: Whether or not the current user has entered the survey.
* *login_url*: The URL to redirect the user to if the survey requires login and they aren't logged in.
* *request*

**embeded_survey_questions.html**

This template displays just the questions and the submit button for the survey entry form. It's used by the Javascript to embed survey entry forms. Reuse code between this template and survey_detail.html. The context is the same for ``survey_detail.html``.

**survey_report.html**

This template displays survey reports. The context is

* *survey*
* *submissions*: A complete list of all the submissions for the survey. You want to avoid this complete list and instead use page_obj.object_list wherever possible. page_obj.object_list lists just those submissions that appear on the page.
* *paginator*: A paginator object that you can probably ignore. Use pages_to_link instead.
* *page_obj*: page_obj.object_list is a list of all the submissions on the page. 
* *pages_to_link*: This handy list contains a useful set of page numbers that might be good to display links for if the survey has a lot of submissions. An example list might be ``[1, False, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, False, 30]`` if you were on page 10 of 30. The idea is that you can display elipses for False.
* *fields*: This list contains all the public questions in the survey.
* *archive_fields*: This list contains all the public questions that would display well in a reverse chronological list of individual submissions. For example, text questions like, "Describe your childhood," display best as a list of submissions. 
* *filters*: This list contains the crowdsourcing.models.Filter objects that correspond to filterable questions in the survey.
* *report*: The survey report.
* *page_answers*: This is a dictionary where the key is the submission id. The value is a list of answers for that submission. This is an optimization. Rather than querying for every submission's answers, we load them all at once and look them up in memory. This dictionary will contain entries for all the submissions in page_obj.object_list.
* *request*

**embeded_survey_report.html**

You can also embed survey reports using the Javascript that comes with the example application. Embedded reports render with this template. As you would expect, you should reuse code between survey_report.html and embeded_surey_report.html.

See the context for survey_report.html

**submission.html**

This template renders the permalinks for individual submissions.

The context is

* *submission*

**submission_for_map.html**

The Javascript that comes with the example app, along with some template tags, renders Google Maps. You can click on icons which will pop a box up over the map with the contents of that submission. This is the template for that popped up box. Again, it makes sense to reuse template code between submission.html and submission_for_map.html. 

See submission.html for the context.

Javascript
==========

The example app comes with some pretty handy Javascript. It embeds surveys and survey reports, renders charts and maps, and so on. As the Javascript generates a certain amount of HTML, it may not fit your site's structure exactly so you'll want to use it with caution. However, it's still a great place to start and you may want to include it directly on your site.

Both the example application and WNYC's website, crowdsourcing's flagship site, use crowdsourcing's Javascript. The Javascript assumes that all crowdsourcing urls are under /crowdsourcing/, i.e., you have a urls.py file with the line ``(r'^crowdsourcing/', include('crowdsourcing.urls'))``.

survey.js uses different markup for surveys that consist of a single choice type question. This markup allows you to enter such a survey with a single click.

Template Tags
=============

These are the more important template tags. For a complete list, view the source at crowdsourcing/templatetags/crowdsourcying.py.

**yahoo_api()**

YUI charts and graphs are pretty slick. The example app is set up to do pie, bar, and line charts using YUI. You will want this tag in your page header to enable YUI.

**jquery_and_google_api()**

Make sure you set the CROWDSOURCING_GOOGLE_MAPS_API_KEY setting discussed below in Settings. Put this tag in your header to load both the Google Maps API and jQuery.

**filters_as_ul(filters)**

Use this template tag to render all the filters for a survey.

**filter_as_li(filter)**

If you want to stick some of your own filters in there, you can have more control over where the filters appear by rendering them individually.

**yahoo_pie_chart(display, question, request_get)**

Render a YUI pie chart.

**yahoo_bar_chart(display, request_get)**

Or a YUI bar chart.

**yahoo_line_chart(display, request_get)**

Or a YUI line chart.

**google_map(display, question, report)**

Or a Google Map.

**simple_slideshow(display, question, request_GET, css)**

You'll need jQuery's jcarousel to make this work. The example app uses ``<script type="text/javascript" src="/media/jquery.jcarousel.min.js"></script>`` in the page header.

**load_maps_and_charts()**

This simply writes out a script tag that calls ``function loadMapsAndCharts()`` defined in survey.js in the example app.

**Tying it all together**

Here, directly from the example app, is some effective code for rendering all the survey report displays in a survey report.

::

  {% for display in report.get_survey_report_displays %}
    {% if display.is_text %}
      {{ display.annotation|safe }}
    {% else %}{% if display.is_pie %}
      {% for question in display.questions %}
        {% yahoo_pie_chart display question request.GET %}
      {% endfor %}
    {% else %}{% if display.is_map %}
      {% for question in display.questions %}
        {% google_map display question report %}
      {% endfor %}
    {% else %}{% if display.is_bar %}
      {% yahoo_bar_chart display request.GET %}
    {% else %}{% if display.is_line %}
      {% yahoo_line_chart display request.GET %}
    {% else %}{% if display.is_slideshow %}
      {% for question in display.questions %}
        {% simple_slideshow display question request.GET "jcarousel-skin-tango" %}
      {% endfor %}
    {% endif %}{% endif %}{% endif %}{% endif %}{% endif %}{% endif %}
  {% endfor %}
  {% load_maps_and_charts %}

**submission_fields(submission, fields=None, page_answers=None, video_height=360, video_width=288)**

This template tag renders all the answers in a single submission.

**submissions(object_list, fields)**

While this template tag renders all the submissions.

**submission_link(submission, link_detail_survey_none=DETAIL_SURVEY_NONE.SURVEY)**

This template tag creates a link that you would display at the end of a submission. As you display submissions on report pages, on their own permalink pages, and in maps, you want the link to point different places.

::

  DETAIL_SURVEY_NONE.DETAIL = 1 # Point to the submission's permalink
  DETAIL_SURVEY_NONE.SURVEY = 2 # Point to the submission's suvey's default survey report
  DETAIL_SURVEY_NONE.NONE = 3 # Don't display a link.
  
**paginator(survey, report, pages_to_link, page_obj)**

On the survey report page you could use this template tag to display your pagination links.

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

.. _API:

API
===

Crowdsourcing has an api that allows you to query submissions. The results return in reverse chronological order by the date they were submitted. If you are a logged in staff user all submissions and all fields will return regardless of whether or not they are public. Every result always has these fields with the exception of empty fields in xml such as the user when the user was not logged in:

* *submitted_at*: The date and time the submission was submitted in the format yyyy-mm-ddThh:mm:ss, e.g. 2010-05-15T14:22:49.
* *survey*: The slug of the survey for the submission.
* *user*: The username of the user if the user was logged in. The xml format drops this field if the user was not logged in.
* *featured*: True or False
* *is_public*: True or False

URL
"""

It depends where your crowdsourcing root url is. If your urls.py file contains the line ``(r'^crowdsourcing/', include('crowdsourcing.urls')),`` then your url will look something like ``/crowdsourcing/submissions/<format>/?<filters>``

Format
""""""

* *json*
* *csv*: The first row contains the column names.
* *xml*: This format includes only non-empty fields

::

  <submissions>
    <submission>
      <submitted_at>2010-05-18T15:21:16</submitted_at>
      <survey>test_survey</survey>
      <user>dsmith</user>
      <category>Republican</category>
      <first_car>Saturn</category>
    </submission>
    <submission>
      <submitted_at>2010-05-18T15:21:16</submitted_at>
      <survey>test_survey</survey>
      <category>Republican</category>
    </submission>
  </submissions>

* *html*: You will probably use this format for debugging.

Filters
"""""""

You pass filters through query string parameters.

These filters are always available.

* *limit*: Include only these many results.
* *survey*: Return only submissions for this survey, identified by its slug. 
* *user*: The username of the submittor.
* *submitted_from*: Include only submissions submitted on or after this date in the format yyyy-mm-ddThh:mm:ss, e.g. 2010-05-18T15:21:16
* *submitted_to*: Submissions on or before this date in the same format at submitted_from.
* *featured*: Use true to retrieve only featured submissions, and false to retrieve only non-featured submissions.
* *is_public*: Use true to retrieve only public submissions, and false to retrieve only non-public submissions.

If you use the survey filter, you can also use specific filters from that survey. To see what parameters you use exactly for a particular survey, follow these steps:

#. Pull up a report for your survey with filters enabled.
#. Fill out the filters how you would like the API to filter.
#. Click submit.
#. Observe the query string of the page you land on. Use similar query string values to filter the API.

Examples
""""""""

Let's say you have a survey with slug liberals-vs-conservatives with a choice type question with fieldname *affiliation* and options *Liberal* and *Conservative*. This url will pull up a human readable html version of all submissions for that survey.

``/crowdsourcing/submissions/html/?survey=liberals-vs-conservatives``

This will retrieve an xml report of all liberals in that survey.

``/crowdsourcing/submissions/xml/?survey=liberals-vs-conservatives&affiliation=Liberal``

This will retrieve a json report of the 10 most recent featured submissions across the whole site.

``/crowdsourcing/submissions/json/?featured=true&limit=10``

(A)Synchronous Flickr
=====================

Crowdsourcing is set up to synchronously sync with Flickr when you save an answer. Asynchronously is ideal. Here's how to set it up.

#. Set CROWDSOURCING_SYNCHRONOUS_FLICKR_UPLOAD to False
#. Set up a regular call to crowdsourcing.models.Answer.sync_to_flickr() If you have celery installed and working then crowdsourcing/tasks.py should wire that up for you.

See CROWDSOURCING_SYNCHRONOUS_FLICKR_UPLOAD below for more details.

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

**CROWDSOURCING_SYNCHRONOUS_FLICKR_UPLOAD**

Syncing flickr synchronously means that crowdsourcing will attempt to sync on save. This is not ideal because it makes a slow user experience, and failed synching goes unresolved. Crowdsourcing syncs synchronously by default however because asynchronously synching is more difficult to set up. crowdsourcing/tasks.py attempts to set up a celery task, so if you have celery running to can just make this setting false.
