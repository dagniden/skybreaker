from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Replay


@receiver(post_delete, sender=Replay)
def delete_replay_file(sender, instance, **kwargs):
    if instance.file.name:
        storage, name = instance.file.storage, instance.file.name
        transaction.on_commit(lambda: storage.delete(name))
