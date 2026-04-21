from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import VenueProfile, CreatorProfile, AudienceProfile

User = get_user_model()


class AudienceProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.URLField(source='user.avatar', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    age = serializers.IntegerField(read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = AudienceProfile
        fields = [
            'id', 'user_id', 'username', 'display_name', 'bio', 'city', 'country',
            'cover_image', 'date_of_birth', 'interests', 'socials', 'is_public',
            'avatar', 'first_name', 'last_name', 'age', 'created_at',
            'followers_count', 'following_count', 'is_following',
        ]
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            # DOB is PII — never expose publicly. Shown only to the owner.
            'date_of_birth': {'write_only': True},
        }

    def get_followers_count(self, obj):
        return obj.user.followers.count() if obj.user_id else 0

    def get_following_count(self, obj):
        return obj.user.following.count() if obj.user_id else 0

    def get_is_following(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated or not obj.user_id:
            return False
        if request.user.id == obj.user_id:
            return False
        return request.user.following.filter(following_id=obj.user_id).exists()


class VenueProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = VenueProfile
        fields = [
            'id', 'user_id', 'username',
            'organization_name', 'organization_type', 'address', 'city',
            'state', 'country', 'zip_code', 'latitude', 'longitude',
            'description', 'logo', 'cover_image', 'is_featured',
            'walkability_score', 'transit_score', 'bike_score',
            'parking_info', 'nearby_transit', 'created_at',
            'followers_count', 'following_count', 'is_following',
        ]
        read_only_fields = ['id', 'is_featured', 'created_at']

    def get_followers_count(self, obj):
        return obj.user.followers.count() if obj.user_id else 0

    def get_following_count(self, obj):
        return obj.user.following.count() if obj.user_id else 0

    def get_is_following(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated or not obj.user_id:
            return False
        if request.user.id == obj.user_id:
            return False
        return request.user.following.filter(following_id=obj.user_id).exists()


class CreatorProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.URLField(source='user.avatar', read_only=True)
    bio = serializers.CharField(source='user.bio', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = CreatorProfile
        fields = [
            'id', 'user_id', 'username', 'display_name', 'specialty', 'skills', 'portfolio_url',
            'showreel_url', 'years_experience', 'city', 'country',
            'avatar', 'bio', 'first_name', 'last_name',
            'is_featured', 'created_at',
            'followers_count', 'following_count', 'is_following',
        ]
        read_only_fields = ['id', 'is_featured', 'created_at']

    def get_followers_count(self, obj):
        return obj.user.followers.count() if obj.user_id else 0

    def get_following_count(self, obj):
        return obj.user.following.count() if obj.user_id else 0

    def get_is_following(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated or not obj.user_id:
            return False
        if request.user.id == obj.user_id:
            return False
        return request.user.following.filter(following_id=obj.user_id).exists()


class UserSerializer(serializers.ModelSerializer):
    venue_profile = VenueProfileSerializer(read_only=True)
    creator_profile = CreatorProfileSerializer(read_only=True)
    audience_profile = AudienceProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'avatar', 'bio', 'phone', 'website', 'is_verified',
            'venue_profile', 'creator_profile', 'audience_profile',
        ]
        read_only_fields = ['id', 'is_verified']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=True)
    # Venue fields
    organization_name = serializers.CharField(required=False, allow_blank=True)
    organization_type = serializers.CharField(required=False, allow_blank=True, default='gallery')
    # Creator fields
    display_name = serializers.CharField(required=False, allow_blank=True)
    specialty = serializers.CharField(required=False, allow_blank=True, default='immersive')
    # Audience fields (display_name reused — works for audience too)
    city = serializers.CharField(required=False, allow_blank=True, default='')
    country = serializers.CharField(required=False, allow_blank=True, default='US')
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    interests = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'organization_name', 'organization_type',
            'display_name', 'specialty',
            'city', 'country', 'date_of_birth', 'interests',
        ]

    def validate(self, data):
        role = data.get('role')
        if role == 'venue' and not data.get('organization_name'):
            raise serializers.ValidationError({'organization_name': 'Required for venue accounts.'})
        if role == 'creator' and not data.get('display_name'):
            raise serializers.ValidationError({'display_name': 'Required for creator accounts.'})
        if role == 'audience' and not data.get('display_name'):
            raise serializers.ValidationError({'display_name': 'Required for audience accounts.'})
        return data

    def create(self, validated_data):
        org_name = validated_data.pop('organization_name', '')
        org_type = validated_data.pop('organization_type', 'gallery')
        display_name = validated_data.pop('display_name', '')
        specialty = validated_data.pop('specialty', 'immersive')
        city = validated_data.pop('city', '')
        country = validated_data.pop('country', 'US')
        date_of_birth = validated_data.pop('date_of_birth', None)
        interests = validated_data.pop('interests', [])
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        if user.role == 'venue':
            VenueProfile.objects.create(
                user=user,
                organization_name=org_name,
                organization_type=org_type,
                city=city,
                country=country or 'US',
            )
        elif user.role == 'creator':
            CreatorProfile.objects.create(
                user=user,
                display_name=display_name,
                specialty=specialty,
                city=city,
                country=country or 'US',
            )
        elif user.role == 'audience':
            AudienceProfile.objects.create(
                user=user,
                display_name=display_name,
                city=city,
                country=country or 'US',
                date_of_birth=date_of_birth,
                interests=interests,
            )

        return user
