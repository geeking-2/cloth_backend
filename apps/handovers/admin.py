from django.contrib import admin
from .models import HandoverReceipt


@admin.register(HandoverReceipt)
class HandoverReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'rental', 'moment', 'owner_sms_verified', 'renter_sms_verified', 'created_at')
    list_filter = ('moment', 'owner_sms_verified', 'renter_sms_verified')
