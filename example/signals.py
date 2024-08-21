from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import VirtualsAccountings, UserProfiles
from .services import PayVesselService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfiles.objects.create(user=instance)
    instance.userprofiles.save()
