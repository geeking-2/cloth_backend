from rest_framework import serializers
from .models import Proposal, PortfolioProject, PortfolioImage
from apps.accounts.serializers import CreatorProfileSerializer


class PortfolioImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioImage
        fields = ['id', 'image_url', 'caption', 'order']


class PortfolioProjectSerializer(serializers.ModelSerializer):
    images = PortfolioImageSerializer(many=True, read_only=True)
    creator_name = serializers.CharField(source='creator.display_name', read_only=True)

    class Meta:
        model = PortfolioProject
        fields = [
            'id', 'title', 'description', 'technology', 'year',
            'cover_image', 'video_url', 'external_url', 'tags',
            'gallery_images', 'videos', 'external_links',
            'client_name', 'role', 'brief', 'outcome', 'metrics',
            'images', 'creator_name', 'created_at',
        ]

    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user.creator_profile
        return super().create(validated_data)


class ProposalSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='creator.display_name', read_only=True)
    creator_avatar = serializers.URLField(source='creator.user.avatar', read_only=True)
    space_title = serializers.CharField(source='space.title', read_only=True)
    venue_name = serializers.CharField(source='space.venue.organization_name', read_only=True)

    class Meta:
        model = Proposal
        fields = [
            'id', 'title', 'description', 'project_type',
            'proposed_start_date', 'proposed_end_date', 'budget',
            'technical_requirements', 'audience_description',
            'status', 'venue_notes', 'creator', 'space',
            'creator_name', 'creator_avatar', 'space_title', 'venue_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'creator', 'status', 'venue_notes', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user.creator_profile
        validated_data['status'] = 'submitted'
        return super().create(validated_data)
