from django import forms
from django.forms.formsets import formset_factory

class ParcelDescriptionForm(forms.Form):
    """
    Form for the creation of parcels/shipments. A ModelForm is not used because
    I need to separate the box dimensions from the Box model
    """
    class Media:
        js = ['admin/js/jquery.min.js', 'admin/js/jquery.init.js', 'admin/js/inlines.js']

    length = forms.DecimalField(max_digits=4, decimal_places=1)
    width = forms.DecimalField(max_digits=4, decimal_places=1)
    height = forms.DecimalField(max_digits=4, decimal_places=1)
    weight = forms.DecimalField(max_digits=5, decimal_places=3)

ParcelDescriptionFormSet = formset_factory(form=ParcelDescriptionForm)