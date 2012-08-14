satchmo-canada-post-developer-program
=====================================

Satchmo shipping module for the new Canada Post Developer Program

binpack algorithm from https://github.com/hudora/pyShipping/

REQUIREMENTS
============
This package requires django-jsonfields and python-canada-post, which can be
found in https://bitbucket.org/bclermont/python-canada-post-dev-prog

USAGE
=====
To use this package you need to setup an account with Canada Post Development
Program (https://www.canadapost.ca/cpotools/apps/drc/home?execution=e1s1) and
get production+development API keys.

Then you need to add it to `INSTALLED_APPS`, and to `CUSTOM_SHIPPING_MODULES` in
`SATCHMO_SETTINGS` in your settings.py:

    INSTALLED_APPS = [
        ...
        'canada_post_dp_shipping',
        ...
    ]

    SATCHMO_SETTINGS = {
        ...
        'CUSTOM_SHIPPING_MODULES': ['canada_post_dp_shipping'],
        ...
    }

after running `$ ./manage.py syncdb` or `$ ./manage.py migrate` if you're using
south (recommended) you can go to your livesettings page (e.g.:
`http://localhost:8000/store/settings/`), activate the Canada Post Developer
Program shipping module in Shipping, save, and set up your API keys and other
settings in the Canada Post Developer Program settings.

Then you need to define your box sizes in `/admin/canada_post_dp_shipping/box/`

Once it's working, the module will contact Canada Post's GetRates product to
supply the buyer with shipping costs. After the user selects the shipping method
a signal creates an Order Shipping Service instance, and a Parcel instance for
each parcel in the precalculated (and charged) shipping order.

To create the shipments with Canada Post and print the shipping labels, you must
visit the OrderShippingService admin page at `/admin/canada_post_dp_shipping/ordershippingservice/`,
once the order is packaged, CHECK that the described Parcel objects reflect the
actual sizes and weights of the packed parcels, and then hit Create Shipments on
the upper right corner of that admin page, and then the "download labels"
(this might take a couple of minutes on Canada Post's side to work).

Soon that last step will be automatizable via djcelery
