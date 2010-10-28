********************
Editing Live Surveys
********************

Editing live surveys is dangerous and you should avoid it whenever possible. If you find yourself in a situation where you have to modify live surveys, pay close attention to these guidelines. 

Submission
==========

Submissions are fairly safe to modify. Be careful to spell the answers correctly for choice type questions or you may end up with a rogue pie chart slice. Also be sure to respect required fields.

Survey Report
=============

Survey reports are safe to modify because they don't affect the data coming into a survey. If you make a mistake you can always fix it. You should be somewhat careful about modifying the slug in case someone has hard linked to the old url. 

Survey
======

Surveys and their questions are tricky. For each field I will explain if it's safe to modify on a live survey. You have to be particularly careful with questions.

**Title**

Safe.

**Slug**

The slug affects urls, so be careful about modifying the slug if you already have links to this survey or its results.

**Tease, Description, Thanks**

Safe.

**Require login, Allow multiple submissions, Moderate submissions**

Safe.

**Allow comments, Allow voting**

These are safe to modify. If you turn them off, the data you have in place does not go away, yet it does stop affecting the user interface.

**Archive policy, Starts at, Ends at, Is published, Email, Site**

Safe.

**Flickr group name**

If you change Flickr groups, the old photos will stay in the old Flickr group.

**Default report**

Safe.

Question
========

**Adding and Removing Whole Questions**

You won't break anything if you add or remove whole questions, but there are some things to be cognizant of. If you add a required question late in the game, you may confuse very detail oriented users who may remark, "Wait, this required question was only answered 100 times, but 200 people entered the survey. My world view is crumbling!" If you remove a whole question, Crowdsourcing will also delete all the answers to that question. This means that if you add the question back in later, you've lost that data.

**Fieldname**

You must be very careful when modifying this field because Survey Report Displays reference questions by fieldname. If you do modify the fieldname, make sure you also update all corresponding Survey Report Displays or you will break your reports.

**Question, Label, Help text**

You can modify these except you should be very careful to not change the meaning of the question. Users who have already answered did so for the old question, so if you change the meaning of the question you'll have answers for two different questions.

**Required**

It is safe to change from being required to not being required. However, the other direction is not safe. If this question starts as not required, then you may have some existing entries that didn't answer this question even though it is now required.

**Order**

Safe.

**Option type**

Generally, changing the option type is madness. There are a few acceptable exceptions.

* You can safely change between integer text box and decimal text box questions. If you change from decimal to integer then all answers that had decimal points will be rounded to integers.
* Text area and text box questions are interchangeable.
* Drop down list and radio button list questions are interchangeable.
* Numeric drop down list and numeric radio button list questions are interchangeable.

**Options**

Counterintuitively, options are very dangerous to change. You can safely change the order of your options. You must not delete or modify options, or users who chose those options already will now have invalid answers that you will have to fix manually. You can, at your own risk, add options. The only problem here is that your users who entered the survey already may have chosen those new answers, so their existing answers aren't accurate.

**Map icons, Answer is public, Use as filter**

Safe.
