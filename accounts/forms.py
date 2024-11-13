from allauth.account.forms import ChangePasswordForm, LoginForm


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super(CustomLoginForm, self).__init__(*args, **kwargs)
        self.fields["password"].help_text = ""


class CustomChangePasswordForm(ChangePasswordForm):
    def save(self):
        super(CustomChangePasswordForm, self).save()
        self.user.force_password_update = False
        self.user.save()
