from django import forms
from .models import Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["date", "type", "category", "description", "amount"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }
