# -*- coding=UTF-8
"""
Canada Post Developer Program Shipping Module
"""
from django.utils.translation import ugettext_lazy as _
from livesettings import *

SHIP_MODULES = config_get('SHIPPING', 'MODULES')
SHIP_MODULES.add_choice(('canada_post_dp_shipping',
                         'Canada Post Developer Program'))

SHIPPING_GROUP = ConfigurationGroup('canada_post_dp_shipping',
                                    _('Canada Post Shipping Dev Prog Settings'),
                                    requires = SHIP_MODULES,
                                    requiresvalue='canada_post_dp_shipping',
)

# values that are needed for later use
ContractShipping = BooleanValue(SHIPPING_GROUP,
                                'CONTRACT_SHIPPING',
                                description=_('Contract Shipping'),
                                help_text=_('Use Contract Shipping method'),
                                default=True)

config_register_list(

    BooleanValue(SHIPPING_GROUP,
                 'LIVE',
                 description=_('Access production Canada Post server'),
                 help_text=_("Use this when your store is in production. "
                             "NOTE: the values you'll see when in development "
                             "mode will NOT reflect the real packaging. This "
                             "is a Canada Post limitation"),
                 default=False),

    StringValue(SHIPPING_GROUP,
                'CUSTOMER_NUMBER',
                description=_('Canada Post Customer Number'),
                help_text=_('The Customer Number assigned by Canada Post'
                            'Developer Program'),
                default=u'CPC_DEMO_XML'),

    StringValue(SHIPPING_GROUP,
                'USERNAME',
                description=_('Canada Post Username'),
                help_text=_('The Canada Post username part of the production '
                            'API production Key Number'),
                default=u'CPC_DEMO_XML'),

    StringValue(SHIPPING_GROUP,
                'USERNAME_DEBUG',
                description=_('Canada Post Username (Debug)'),
                help_text=_('The Canada Post username part of the development '
                            'API Key Number'),
                default='CPC_DEMO_XML'),

    StringValue(SHIPPING_GROUP,
                'PASSWORD',
                description=_('Canada Post Password'),
                help_text=_('The Canada Post password part of the production '
                            'API Key Number'),
                default=u'CPC_DEMO_XML'),

    StringValue(SHIPPING_GROUP,
                'PASSWORD_DEBUG',
                description=_('Canada Post Password (Debug)'),
                help_text=_('The Canada Post password part of the development '
                            'API Key Number'),
                default=u'CPC_DEMO_XML'),

    ContractShipping,

    StringValue(SHIPPING_GROUP,
                'CONTRACT_NUMBER',
                description=_('Contract Number'),
                help_text=_('The contract number with Canada Post. Required '
                            'for Contract Shipment'),
                requires=ContractShipping,
                default='CPC_DEMO_XML'),

    MultipleStringValue(SHIPPING_GROUP,
                        'SHIPPING_CHOICES',
                        description=_("Canada Post shipping choices available to customers."),
                        choices = (
                            ('DOM.RP', 'Regular Parcel'),
                            ('DOM.EP', 'Expedited Parcel'),
                            ('DOM.XP', 'Xpresspost'),
                            ('DOM.XP.CERT', 'Xpresspost Certified'),
                            ('DOM.PC', 'Priority'),
                            ('DOM.LIB', 'Library Books'),
                            ('USA.EP', 'Expedited Parcel USA'),
                            ('USA.PW.ENV', 'Priority Worldwide Envelope USA'),
                            ('USA.PW.PAK', 'Priority Worldwide pak USA'),
                            ('USA.PW.PARCEL', 'Priority Worldwide Parcel USA'),
                            ('USA.SP.AIR', 'Small Packet USA Air'),
                            ('USA.SP.SURF', 'Small Packet USA Surface'),
                            ('USA.XP', 'Xpresspost USA'),
                            ('INT.XP', 'Xpresspost International'),
                            ('INT.IP.AIR', 'International Parcel Air'),
                            ('INT.IP.SURF', 'International Parcel Surface'),
                            ('INT.PW.ENV', 'Priority Worldwide Envelope Int’l'),
                            ('INT.PW.PAK', 'Priority Worldwide pak Int’l'),
                            ('INT.PW.PARCEL', 'Priority Worldwide parcel Int’l'),
                            ('INT.SP.AIR', 'Small Packet International Air'),
                            ('INT.SP.SURF', 'Small Packet International Surface'),
                            ),
                        default = ('DOM.EP', 'DOM.XP', 'DOM.XP.CERT',
                                   'DOM.PC',)),

    BooleanValue(SHIPPING_GROUP, 'RAISE_TOO_LARGE',
                 description=_("Raise Too Large errors"),
                 help_text=_("Raise a ParcelTooLarge exception when a parcel "
                             "cannot be handled by Canada Post"),
                 default=False),

    BooleanValue(SHIPPING_GROUP,
                 'VERBOSE_LOG',
                 description=_("Verbose logs"),
                 help_text=_("Send the entire request and response to the log - for debugging help when setting up Canada Post."),
                 default=False)
)
