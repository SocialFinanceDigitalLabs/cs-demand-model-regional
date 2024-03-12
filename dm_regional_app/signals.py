from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from dm_regional_app.models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if ".gov.uk" in instance.email:
            la = instance.email.split("@")[1].split(".")[0]
        else:
            la = None
        Profile.objects.create(user=instance, la=la)
