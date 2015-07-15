.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Runbot pylint
===========

This module was written to extend the functionality of runbot to support pylint command
and allow you to check fails of lint.

You can select type of error to test, path to test, ignore files... from a git repo with pylint configuration files.

Installation
============

To install this module, you need to:

* See main root README of this repository.
* Install `pylint` package: `pip install pylint`

Configuration
=============

To configure this module, you need to:

* Create a new repository git with your pylint conf file.
* Create new `runbot.repo` record of your new repository git of pylint conf file.
* Set relative path of your pylint conf file in `runbot.repo` in field `pylint_conf` and add in dependency repo your pylint repo.

Usage
=====

To use this module, you need to:

* Go to your new build and check yellow fails.
* Go to link of pylint log in builds of /runbot page.

For further information, please visit:

* https://www.odoo.com/forum/help-1

Known issues / Roadmap
======================

* (empty)

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/runbot-addons/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/runbot-addons/issues/new?body=module:%20runbot_pylint%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


Credits
=======

Contributors
------------

* Moises Lopez <moylop260@vauxoo.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.

