*******************
Objects and Options
*******************

Submission
==========

Crowdsourcing creates a submission when a user correctly fills out a
survey and submits the form. A submission is comprised of 0 or more
answers.

**Survey**

Each submission is associated with exactly one survey.

**User**

If the person filling out the survey is logged in, crowdsourcing will
set this field regardless of whether or not log in is required for the
survey.

**Ip address**

If the survey does not require logged in users and does not allow
multiple submissions, crowdsourcing uses the ip address to stop
multiple submissions. In all cases, it is also recorded for any
forensic value it might have.  Crowdsourcing pulls the ip address from
the http request, and attempts to honor the ``X-Forwarded-For`` header
added by many proxies; however, it is still possible multiple users
behind a router could have the same ip address, or that the ip address
is spoofed or otherwise inaccurate, so don't consider the values
stored here as definitive.

**Submitted at**

This time reflects the time zone of the server that received the
request, not the time zone of the user.

**Featured**

This flag is useful for featuring specific submissions. How featured
submissions are displayed exactly is particular to your site.

**Is public**

You set this flag manually in the admin. Only public submissions
appear on the site. This includes charts and graphs like maps and pie
charts. Surveys have a "moderate submissions" field which determines
the default "is public" value. Moderated surveys have not public
submissions which may be switched to public. Not moderated surveys
have public submissions which may be switched to not public.

Answer
======

An answer is a single answer to a specific question. A submission is
made up of answers. Answers appear in the admin as a list under their
submission. You may notice that an answer has several fields, most of
which remain empty. This is because Crowdsourcing uses different
fields depending on the type of question.

.. note:: Why is that?

    Databases are much faster at perfoming mathematical operations
    like average and sum on numeric columns. If you have a question
    like, "How much did your car cost?" and you want to display the
    average cost, it makes the most sense to place those answers in a
    numeric database column. On the other hand, you may have questions
    like, "What was your first car like?" which clearly require a text
    answer.

**Text answer**

This field is used for any question that is best recorded as text,
e.g. "What's your address?"

**Integer answer**

This column is used for whole numbers.

**Float answer**

This column is used for decimals. Any integer answer will also be
recorded as a float answer and visa versa. This is in case someone
changes the type of question between integer and float.

**Boolean answer**

i.e. true / false questions.

**Image answer**

This will be the path to the file that the user uploaded.

**Latitude**

In degrees between -90 and 90.

**Longitude**

In degrees between -90 and 90.

**Flickr id**

If you set up crowdsourcing to work with Flickr, you associate a
survey with a Flickr group, and a user uploads a photo, this field
will contain the id that Flickr uses to identify the photo. This is an
advanced field that you should never need to fix manually.

Survey
======

A survey is a set of options and a list of questions.

**Title**

The title appears at the top whenever crowdsourcing displays surveys
or their results.

**Slug**

The slug is used to build urls. Every survey must have a new unique slug.

**Tease**

The tease may be used to briefly describe the survey.

**Description**

The description appears after the title on detail pages.

**Thanks**

When a user submits an entry they will either be redirected to the
results, or will be shown this thanks message, whichever is
appropriate.

**Require login**

When set, only logged in users can enter this survey.

**Allow multiple submissions**

If you don't allow multiple submissions and don't require login, then
Crowdsourcing will use the ip address of users who are not logged in
to block multiple submissions.

**Moderate submissions**

If you choose to moderate submissions then every submission will start
out as not public for this survey.

**Allow comments**

Can users comment on other users' submissions?

**Allow voting**

Similarly, can users vote on other users' submissions?

**Archive policy**

At what point will Crowdsourcing make the results public?

* *immediate*: All results are immediately public.
* *post-close*: Results are public on or after the "ends at" option documented below.
* *never*: Results are never public.

**Starts at**

When will users be allowed to enter this survey?

**Ends at**

When will users stop being allowed to enter this survey?

**Is published**

Crowdsourcing only displays the entry form and results for published surveys.

**Email**

Send a notification to these e-mail addresses whenever someone submits an entry to this survey. Comma delimited.

**Site**

What site is this survey associated with? 

**Flickr group name**

Use the exact group name from flickr.com. If you use this field, then
all images uploaded to this survey will also be uploaded to the
specified group on Flickr.

**Default report**

Survey reports describe how you should display the results of a
survey. If you specify a default report then Crowdsourcing will use
that report to display the results of a survey unless they request a
specific different report. You request specific reports by using the
urls pattern
``http://yoursite.com/crowdsourcing/survey-slug/survey-report-slug/``. If
you don't specify a default report then Crowdsourcing will use its
default behavior.

The default report behavior is to display the filters and individual
results. It creates one pie chart for every choice type question, and
one map for every location text box question.

Question
========

A survey contains a list of questions. Drop Down List, Radio Button
List, Numeric Drop Down List, Numeric Radio Button List, and Checkbox
questions are choice type questions. These are useful as categories.

**Fieldname**

The fieldname is a single-word identifier used to track a question. It
must begin with a letter and may contain alphanumerics and underscores
(no spaces). Fieldnames must be unique within a survey, but you can
reuse the same fieldname in different surveys.

**Question**

The question appears on the survey entry form. You might use, "How
much did your first car cost?"

**Label**

The label, on the other hand, appears on report pages. You might use,
"My first car cost this much"

**Help text**

The help text appears below the question on the survey entry form. Use
it to clarify what your question means or to give further
instructions.

**Required**

Is an answer to this question required?

**Order**

This must be an whole number. Crowdsourcing will sort questions by
this field when deciding what order to display questions in.

**Option type**

What type of question is this?

* *Checkbox*: Use a checkbox for Yes / No type questions. If you make a checkbox question required, then crowdsourcing requires the user to check the box. You would use this for a EULA. 
* *Checkbox List*: Sometimes you have a list of checkboxes but you don't want to bother making a new question for every checkbox. The downside to checkbox lists is that they don't work in aggregate results like pie charts.
* *Decimal Text Box*: The user will only be able to enter a decimal number. This type of question is good for money questions.
* *Drop Down List*: This choice type question displays the options in a drop down list.
* *Email Text Box*: This text box has minimal validation for a valid e-mail address.
* *Integer Text Box*: The user will only be able to enter a whole number.
* *Location Text Box*: This type of question is good for addresses. Crowdsourcing can display maps for address questions.
* *Numeric Drop Down List*: This choice type question takes only numbers as options. You could use this type of question for ratings.
* *Numeric Radio Button List*: This choice type question is identical to the Numeric Drop Down List type except that it displays the options as a radio button list.
* *Photo Upload*: Photo uploads will allow the user to upload a single photo. If this survey has Flickr support the photo will also upload to Flickr.
* *Radio Button List*: This choice type question is identical to the Drop Down List type except that it displays the options as a radio button list.
* *Text Area*: A text area will allow the user to enter an arbitrary amount of text. Use this type for essay type questions.
* *Text Box*: This text type is more suited for very short text answers.
* *Video Link Text Box*: Users can enter a url to a video which Crowdsourcing will then embed on the page when it displays results.

**Options**

All choice type questions requre a list of options. Put each option on
its own line. For Numeric Drop Down List and Numeric Radio Button List
questions every option must be a number. You can use a mix of decimals
and whole numbers.

**Map icons**

Lets say you want to display your users' submissions on a map and use
different map icons depending on the user. You will need to include a
choice type question. For each option include a corresponding map icon
url. For example, you could have a Drop Down List question with the
options Pigs, Cows, and Hens. Then you could create pig, cow, and hen
icons and place them on your server at /images/pig.png,
/images/cow.png, and /images/hen.png. You would place those urls
separated by lines in the map icons field. You may be tempted to put
your Map icons in your Location Text Box question, but this is
incorrect.

**Answer is public**

Questions whose answers are not public will not display anywhere in
Crowdsourcing. Staff members can still access these answers in the
admin. You would likely not make an e-mail question public for
example.

**Use as filter**

On a survey report you have the option to display filters. Different
questions display as different kinds of filters. On survey reports
that use filters, this flag determines whether or not to display a
filter for this question. Not all questions make sense as filters. For
example, Crowdsourcing ignores this flag for Photo Upload
questions. We cover filters in more depth later.

Survey Report
=============

Survey reports describe how you would like to display the results for
your survey. Survey reports are a collection of options and optionally
a list of Survey Report Displays.

**Survey**

You associate a survey report with a single survey.

**Title**

The title displays on the survey report page. If you leave this field blank, crowdsourcing will use the survey title.

**Slug**

You may reuse slugs so long as the same survey has only one survey
report per slug. Slugs are used to build urls that display specific
surveys using specific reports, e.g.,
``http://yoursite.com/crowdsourcing/survey-slug/survey-report-slug/``.

**Summary**

The summary displays on the survey report page below the title. You can use html. If you leave this field blank, crowdsourcing will use the survey description. If that is blank, crowdsourcing will use the survey tease as a last result.

**Sort by rating**

You can sort submissions either descending by the when they were
submitted, or descending by their rating.

**Display the filters**

When you view this survey report, should Crowdsourcing display the
filters at the top of the page?

**Limit results to**

This option limits the number of results that Crowdsourcing
displays. You could use it to make a top 10 list.

**Featured**

Include only featured submissions.

**Display individual results**

If you only want to display aggregate results like pie charts you can
use this flag to turn off individual results.

Survey Report Display
=====================

Think of Survey Report Displays as line items in Survey Reports. The
describe a specific thing you would like to show up in the survey
report.

**Display type**

* *text*: Simply insert the annotation directly in the report. This is useful for including raw html.
* *pie*: Pie charts require 1 or more fieldnames. Crowdsourcing will draw one pie chart for every fieldname. Choice type and checkbox questions are best for pie charts. Questions with a large number of possible answers such as decimal text box questions will have many slices and won't make sense. Pie charts require either the default or count aggregate type. Pie charts can't have an x axis fieldname as this doesn't make sense. Pie charts will have a slice for every option that at least one user picked.
* *map*: Maps require 1 or more fieldnames. Only location questions make sense. Crowdsourcing will draw a map and put a marker down for every submission that has a recognizable address in the question referenced in the fieldnames.
* *bar*: Bar charts have an x axis and 1 or more y axes, entered in the fieldnames.
* *line*: Line charts are identical to bar charts except that they use connected lines between points instead of vertical bars.
* *slideshow*: Crowdsourcing will display one slideshow per fieldname. Only photo upload questions make sense as slideshows.
* *download*: Display links that allow the user to download the survey results in several formats, e.g. csv.

**Fieldnames**

Fieldnames is a space delimited list of questions referenced by their
fieldname. Usually you have to include at least one fieldname or your
survey report display won't do anything. Exceptions include text which
simply inserts raw html, and bar or line charts that use the count
aggregate type. For bar and line charts the fieldnames will become the
y axes. For pie charts each fieldname will become a single pie
chart. Maps will display one map per location fieldname.

**Annotation**

The annotation is raw html that you can insert for any survey report display.

**Order**

Crowdsourcing displays survey report displays in ascending order. You
can specify the order as -1 if you would like crowdsourcing to
automatically pick where to place your Survey Report Display, usually
at the end.

Pie, Line, and Bar Charts
"""""""""""""""""""""""""

**Aggregate type**

The aggregate type is only useful for Line and Bar charts. It
describes how you would like to combine the values in the y
axes. Let's say you had a drop down list question for the x axis that
let you pick the model of your first car. Now let's say you had a
decimal text box question as a y axis where the user could say how
much their first car cost. User A says their first car was a Toyota
and cost 5000.00. User B says their first car was a Toyota and cost
1000.00. If you choose the default or sum aggregate type then the
chart will use set the Toyota value at 6000.00. Average will set the
Toyota value to 3000.00. Count will use 2, meaning that 2 people
entered a cost for Toyota.

.. note:: Pie charts and aggregate type

    For pie charts the default, and only valid mathematical function,
    is count. You can switch pie charts from default to count but
    there's no point.

* *default*: Most of the time you will probably just choose default. For Line and Bar charts the default is sum. For pie charts the default is count.
* *sum*: Sum adds all of the y axis values together.
* *count*: Count computes how many valid answers exist but ignores the actual values of those answers.
* *average*: Average computes the average y axis value.

**X axis fieldname**

The x axis is only valid for line and bar charts. Like fieldnames, use
the fieldname of a question from the survey. You may only specify a
single x-axis. Choice type questions, numeric questions, and checkbox
questions all work well for the x axis. If you choose a numeric x axis
then the x axis will be ordered and continuous as you would
expect. Otherwise for non-numeric choice type questions the x axis
values will appear in the same order as the options in the question.

Slideshow
"""""""""

**Caption fields**

The answers to these questions will appear as captions below their
corresponding slides. Separate by spaces.

Maps
""""

**Limit map answers**

Google maps gets pretty slow if you add too many points. Use this
field to limit the number of points that display on the map.

**Map center latitude**

If you don't specify latitude, longitude, or zoom, the map will just
center and zoom so that the map shows all the points.

**Map center longitude**

Latitude and longitude are in degrees between -90.0 and 90.0. Maps
only use either value if you specify both.

**Map zoom**

13 is about the right level for Manhattan. 0 shows the entire world.
