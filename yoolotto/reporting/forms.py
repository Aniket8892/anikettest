from django import forms
from yoolotto.dashboard_app.models import Entries

class EntriesForm(forms.ModelForm):
	class Meta:
		model=Entries
		#exclude = ['ecpm']