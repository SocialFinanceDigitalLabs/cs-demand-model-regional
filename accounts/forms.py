from allauth.account.forms import ChangePasswordForm


class CustomChangePasswordForm(ChangePasswordForm):
    def save(self):
        super(CustomChangePasswordForm, self).save()
        self.user.force_password_update = False
        self.user.save()
