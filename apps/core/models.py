from django.db import models
from django.contrib.auth.models import User

class AuditModel(models.Model):
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs')
    action = models.CharField(max_length=50)
    module = models.CharField(max_length=50)
    object_type = models.CharField(max_length=50, blank=True, default='')
    object_id = models.CharField(max_length=50, blank=True, default='')
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.user} - {self.action} {self.object_type} ({self.object_id})"


def record_audit(user, action, module, object_type='', object_id='', old_data=None, new_data=None):
    try:
        actual_user = user if (user and user.is_authenticated) else None
        return AuditLog.objects.create(
            user=actual_user,
            action=action,
            module=module,
            object_type=object_type,
            object_id=str(object_id) if object_id else '',
            old_data=old_data,
            new_data=new_data
        )
    except Exception as e:
        # Never break main transaction on audit log logging failure
        return None
