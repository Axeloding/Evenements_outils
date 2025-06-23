# events/forms.py
from django import forms

class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Fichier Excel à importer",
        help_text="Le fichier doit avoir été géocodé et contenir les colonnes attendues.",
        widget=forms.ClearableFileInput(attrs={
            'accept': '.xlsx, .xls',
            'class': 'form-control'
        })
    )