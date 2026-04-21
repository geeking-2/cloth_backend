from rest_framework import serializers
from .models import Space, SpaceImage, Availability, SavedSpace, SpaceAttachment
from apps.accounts.serializers import VenueProfileSerializer


class SpaceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceImage
        fields = ['id', 'image_url', 'caption', 'is_primary', 'order']


class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['id', 'start_date', 'end_date', 'is_available', 'notes']


class SpaceListSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.organization_name', read_only=True)
    venue_city = serializers.CharField(source='venue.city', read_only=True)
    venue_country = serializers.CharField(source='venue.country', read_only=True)
    primary_image = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    latitude = serializers.DecimalField(
        source='venue.latitude', max_digits=9, decimal_places=6, read_only=True
    )
    longitude = serializers.DecimalField(
        source='venue.longitude', max_digits=9, decimal_places=6, read_only=True
    )

    image_urls = serializers.SerializerMethodField()

    class Meta:
        model = Space
        fields = [
            'id', 'title', 'slug', 'space_type', 'area_sqft', 'daily_rate',
            'currency', 'is_featured', 'venue_name', 'venue_city', 'venue_country',
            'primary_image', 'image_urls', 'rating', 'review_count', 'latitude', 'longitude',
            'tags', 'created_at',
        ]

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        return img.image_url if img else ''

    def get_image_urls(self, obj):
        return [img.image_url for img in obj.images.all()[:5]]

    def get_rating(self, obj):
        val = getattr(obj, 'rating', None)
        if val is not None:
            return round(float(val), 1) if val else 0
        return obj.get_rating()

    def get_review_count(self, obj):
        val = getattr(obj, 'review_count', None)
        if val is not None:
            return val
        return obj.get_review_count()


class SpaceAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceAttachment
        fields = ['id', 'title', 'file_url', 'file_type']


class VenueSpaceSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for venue's other spaces table."""
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Space
        fields = [
            'id', 'title', 'slug', 'space_type', 'area_sqft',
            'max_capacity', 'daily_rate', 'weekly_rate', 'monthly_rate',
            'currency', 'is_active', 'primary_image',
        ]

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        return img.image_url if img else ''


class SpaceDetailSerializer(serializers.ModelSerializer):
    venue = VenueProfileSerializer(read_only=True)
    images = SpaceImageSerializer(many=True, read_only=True)
    availabilities = AvailabilitySerializer(many=True, read_only=True)
    attachments = SpaceAttachmentSerializer(many=True, read_only=True)
    venue_spaces = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Space
        fields = [
            'id', 'title', 'slug', 'description', 'space_type',
            'area_sqft', 'ceiling_height_ft', 'max_capacity',
            'has_wifi', 'has_power_outlets', 'has_projection_surfaces',
            'has_sound_system', 'has_blackout_capability', 'has_climate_control',
            'technical_notes', 'daily_rate', 'weekly_rate', 'monthly_rate',
            'currency', 'is_active', 'is_featured', 'tags', 'features',
            'floor_plan_url', 'video_url', 'venue', 'images', 'availabilities',
            'attachments', 'venue_spaces', 'rating', 'review_count',
            'created_at', 'updated_at',
        ]

    def get_venue_spaces(self, obj):
        siblings = Space.objects.filter(
            venue=obj.venue, is_active=True
        ).exclude(id=obj.id).select_related('venue').prefetch_related('images')[:10]
        return VenueSpaceSummarySerializer(siblings, many=True).data

    def get_rating(self, obj):
        val = getattr(obj, 'rating', None)
        if val is not None:
            return round(float(val), 1) if val else 0
        return obj.get_rating()

    def get_review_count(self, obj):
        val = getattr(obj, 'review_count', None)
        if val is not None:
            return val
        return obj.get_review_count()


class SpaceCreateUpdateSerializer(serializers.ModelSerializer):
    image_urls = serializers.ListField(
        child=serializers.CharField(), required=False, write_only=True
    )

    class Meta:
        model = Space
        fields = [
            'title', 'description', 'space_type', 'area_sqft',
            'ceiling_height_ft', 'max_capacity',
            'has_wifi', 'has_power_outlets', 'has_projection_surfaces',
            'has_sound_system', 'has_blackout_capability', 'has_climate_control',
            'technical_notes', 'daily_rate', 'weekly_rate', 'monthly_rate',
            'currency', 'is_active', 'tags', 'video_url', 'image_urls',
        ]

    def create(self, validated_data):
        image_urls = validated_data.pop('image_urls', [])
        validated_data['venue'] = self.context['request'].user.venue_profile
        space = super().create(validated_data)
        for i, url in enumerate(image_urls):
            SpaceImage.objects.create(space=space, image_url=url, is_primary=(i == 0), order=i)
        return space

    def update(self, instance, validated_data):
        image_urls = validated_data.pop('image_urls', None)
        instance = super().update(instance, validated_data)
        if image_urls is not None:
            # Replace all images
            instance.images.all().delete()
            for i, url in enumerate(image_urls):
                SpaceImage.objects.create(space=instance, image_url=url, is_primary=(i == 0), order=i)
        return instance
