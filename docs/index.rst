.. django-crowdsourcing documentation master file, created by
   sphinx-quickstart on Thu Jun  3 17:26:10 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Django-Crowdsourcing
====================

Django-crowdsourcing is a highly configurable survey and report tool
for journalists, with a feature set that supports a wide range of
useful crowdsourcing projects.  It is developed and used at `New York
Public Radio`_ with support from the `Knight Foundation`_, and released
under an MIT license.

.. _`New York Public Radio`: http://www.wnyc.org/
.. _`Knight Foundation`: http://www.knightfoundation.org/

The fundamental content unit this app provides is the survey, which
consists of a list of questions, some presentational metadata -- title
and so on -- and configuration that determines some aspects of how the
survey behaves.  The questions may solicit a variety of different
types of input: text, numbers, choices from drop-down or radio lists,
image uploads, video links, addresses, and more.  Survey forms exist
in both full page and embeddable versions, for maximum flexibility in
presentation.

Users primarily participate by creating submissions which consist of
answers to the survey's questions.  Whether these answers are
published or not is defined on a per-survey basis.  Users may also,
depending on how the survey is configured, be able to comment on
and/or rate each other's contributions.

These submissions, if you wish to display them, may be presented in
one or more survey reports, which represent different views on the
data collected; reports can contain widgets such as pie charts, maps,
slideshows, graphs, and more, as well as filterable archives of the
results and, if you wish, editorial annotations.  If you don't
configure any reports, the application will do its best to generate a
reasonable report given the types of questions asked and the survey
configuration.  Reports, like survey forms, can also be embedded in
other pages.  Or, if you want to create your own mash-up from survey
data, it can be queried by means of a flexible web api.

Django-crowdsourcing is a reusable Django application, designed to be
installed easily in any Django site.  It is site-aware, and thus works 
well in multi-site installations.  Its surveys are entirely configured within 
the admin interface that ships with Django.

While the primary focus of development is support for crowdsourcing
projects, the survey tool is general purpose and can be used for a
variety of applications.  If your website runs on Django and you want
some slick surveys, crowdsourcing is a good way to go. It's easy
enough to handle simple polls with pie charts, yet it's powerful
enough to handle complicated surveys with rich multimedia responses
plotted on a map with custom icons.  And it is under active
development, so expect more features soon.


Contents
========

.. toctree::
   :maxdepth: 2

   producers/index
   developers/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
