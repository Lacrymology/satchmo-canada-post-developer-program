satchmo-canada-post-developer-program
=====================================

Satchmo shipping module for the new Canada Post Developer Program

binpack algorithm from https://github.com/hudora/pyShipping/

USAGE
=====
To use this package you need to setup an account with Canada Post Development
Program (https://www.canadapost.ca/cpotools/apps/drc/home?execution=e1s1) and
get production+development API keys.

Then you need to add it to `INSTALLED_APPS`, and to `CUSTOM_SHIPPING_MODULES` in
`SATCHMO_SETTINGS` in your settings.py:

    SATCHMO_SETTINGS = {
        ...
        'CUSTOM_SHIPPING_MODULES': ['canada_post_dp_shipping'],
        ...
    }
