from django.contrib.admin.sites import site
from django.contrib import admin
from canada_post_dp_shipping.models import Box

class BoxAdmin(admin.ModelAdmin):
    """
    Admin for Box model
    """
    list_display = ['__unicode__', 'girth', 'volume']
site.register(Box, BoxAdmin)