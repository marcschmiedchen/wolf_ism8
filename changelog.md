3.2.5 (2024-12-12)
------------------
Added
~~~~~~~
- some CHA ControlModes which were missing from Wolf documentation

3.2.4 (2024-07-02)
------------------
Fixes
~~~~~~~
- fixed bug in time encoding, again

3.2.3 (2024-07-01)
------------------
Fixes
~~~~~~~
- fixed bug in time encoding

3.2.2 (2024-06-21)
------------------

Fixes
~~~~~~~
- fixed bug in date encoding

3.2.1 (2024-06-21)
------------------

Fixes
~~~~~~~
- fixed some minor bugs, streamlined validation


3.2 (2024-06-14)
------------------

New
~~~
- added reporting of version number
- added data integrity checks

Fixes
~~~~~~~
- fixed errors in datapoint dictionary definition

------------------

3.1 (2024-06-08)
------------------

New
~~~
- added support for TIME and DATE datapoints, read and write
- added callback-functionality to realize push-integration in home assistant

Fixes
~~~~~~~
- one datapoint was missing. Fixed that. 
------------------



3.0 (2024-01-18)
------------------

New
~~~
- added/tested support for writing float datapoints to ISM8
- added undocumented datapoints instead of ignoring them


Changes
~~~~~~~
- breaking change: renamed all devices to full name instead of abbreviation
- breaking change: deprecated function "read" replaced by "read_sensor"


x.x.x
------------------

New
~~~
- Everything
- started changelog at 3.0 (sorry)
