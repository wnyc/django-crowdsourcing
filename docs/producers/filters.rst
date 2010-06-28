*******
Filters
*******

Introduction
============

Filters allow you to control which submissions appear in a survey report. They appear at the top of a survey report. There is at most one filter per question. We currently only support filters for checkbox, choice type, numberic, and location questions.

Types
=====

Choice
""""""

Checkbox, drop down list, numeric drop down list, radio button list, and numeric radio button list questions become a drop down list filter. 

Numeric Text Boxes
""""""""""""""""""

Decimal text box and Integer text box questions become range filters. You can fill in a lower bound and / or an upper bound. If the user enters a lower bound, then Crowdsourcing will only show submissions with an answer to the numeric question at or above the lower bound. The upper bound works similarly except with answers at or below the upper bound.

Location Text Box
"""""""""""""""""

Location text box questions become location filters. You specify a starting address in the first text box and a radius in miles in the second. For example, you could show only submissions with an address within 100 miles of Vancouver, B.C.

Technical Details
=================

The user interface allows a user to fill in the filters however they like and then click a "Submit" button which applies those filters to the report. The page will reload with the values of the filters in the query string.

Crowdsourcing checks the query string values regardless of whether or not the filters are visible. This means that you can create links that apply filters to survey reports where you can't actually see the filters. The "Category" example uses this trick. If you want to create a url you can follow these steps.

  * Turn filters on for your survey report.
  * Fill out the filters and submit.
  * Copy the url that results.
  * Turn the filters off.
  * Now the url you have controls the report even though you can't see the filters.

If a user puts an invalid entry in a filter, such as a non-number in a numeric range filter, crowdsourcing will simply ignore it.

Filters apply to aggregate results such as pie charts. This is pretty interesting actually because it allows the user to slice and dice the information in unique ways. For example, let's say you have a drop down list question, "What's the model of your car?" with the options Saturn and Lamborghini. You may also have a question, "How do you vote?" with options Republican and Other. Now in your survey report you may have a pie chart that shows how may Saturns and Lamborghinis there are total. You also have a filter for how you vote, so a user could set the filter to Republican, and voila, the pie chart now shows how many Republicans drive Saturns.
