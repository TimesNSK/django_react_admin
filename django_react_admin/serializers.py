from rest_framework import serializers


class ActionSerializer(serializers.Serializer):
	id = serializers.JSONField()