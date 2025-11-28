from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class CardCreateForm(forms.Form):

    def __init__(self, *args, board_size=5, **kwargs):
        super().__init__(*args, **kwargs)
        self.board_size = board_size
        center = board_size // 2

        for r in range(board_size):
            for c in range(board_size):
                if r == center and c == center:
                    continue  # middle is free
                name = f"cell_{r}_{c}"
                self.fields[name] = forms.CharField(
                    max_length=100,
                    required=True,
                    label="",            # no labels – grid only
                    widget=forms.TextInput(
                        attrs={"placeholder": "", "autocomplete": "off"}
                    ),
                )

class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username",)