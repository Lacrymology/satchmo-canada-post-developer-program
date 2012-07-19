from django.contrib.admin.sites import site
from django.contrib import admin
from canada_post_dp_shipping.models import (Box, ShippingServiceDetail,
                                            ParcelDescription)

class BoxAdmin(admin.ModelAdmin):
    """
    Admin for Box model
    """
    list_display = ['__unicode__', 'girth', 'volume']
site.register(Box, BoxAdmin)

class ParcelInline(admin.StackedInline):
    model = ParcelDescription
    readonly_fields = ['parcel', 'box']
    extra = 0

class DetailAdmin(admin.ModelAdmin):
    """
    Admin for an order's detail
    """
    inlines = [ParcelInline]
site.register(ShippingServiceDetail, DetailAdmin)
