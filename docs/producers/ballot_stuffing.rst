***********************
Stuffing the Ballot Box
***********************

The best way to prevent ballot box stuffing is to require users to login before they vote using the "Require login" option on surveys. Otherwise, if you are a logged in staff member and have access to :ref:`downloading-survey-submissions`, you can use the submitted_at, ip_address, and session_key columns in the downloadable report to look for telltale signs of ballot box stuffing.

* Lots of votes for a single option in a short time frame with regular intervals.
* Lots of votes for a single option from a single IP address. Keep in mind that many computers often have a single IP address, such as all the computers in an office building. IP addresses are only a clue that point towards ballot stuffing, not necessarily proof.
* Votes with blank session keys. When you clear your cookies, you clear your session and circumvent crowdsourcing's necessarily insecure first line of defense againt ballot stuffing: cookies.
