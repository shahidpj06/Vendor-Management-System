from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, F, Q
from django.utils import timezone
from .models import Vendor, PurchaseOrder, HistoricalPerformance
from .serializers import VendorSerializer, PurchaseOrderSerializer, HistoricalPerformanceSerializer, UserSerializer
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated



class RegisterUser(APIView):
    def post(self, request):
        serializers = UserSerializer(data = request.data)

        if not serializers.is_valid():
            return Response({'status': 403, 'errors': serializers.errors, 'message': 'Something wrong'})
        
        serializers.save()
        user = User.objects.get(username = serializers.data['username'])
        token_obj, _ = Token.objects.get_or_create(user=user)
        return Response({'status': 200, 'payload': serializers.data, 'token': str(token_obj),  'message': 'your data is saved'})

class VendorViewSet(viewsets.ModelViewSet):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]
    
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer

    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        vendor = self.get_object()
        data = {
            'on_time_delivery_rate': vendor.on_time_delivery_rate,
            'quality_rating_avg': vendor.quality_rating_avg,
            'average_response_time': vendor.average_response_time,
            'fulfillment_rate': vendor.fulfillment_rate
        }
        return Response(data)

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer

    def perform_create(self, serializer):
        purchase_order = serializer.save()
        self.update_performance_metrics(purchase_order.vendor)

    def perform_update(self, serializer):
        purchase_order = serializer.save()
        self.update_performance_metrics(purchase_order.vendor)

    def perform_destroy(self, instance):
        vendor = instance.vendor
        instance.delete()
        self.update_performance_metrics(vendor)

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        purchase_order = self.get_object()
        purchase_order.acknowledgment_date = timezone.now()
        purchase_order.save()
        self.update_performance_metrics(purchase_order.vendor)
        return Response({'status': 'acknowledged'})

    def update_performance_metrics(self, vendor):
        completed_orders = PurchaseOrder.objects.filter(vendor=vendor, status='completed')

        if completed_orders.exists():
            # On-Time Delivery Rate
            on_time_deliveries = completed_orders.filter(delivery_date__lte=F('delivery_date')).count()
            vendor.on_time_delivery_rate = (on_time_deliveries / completed_orders.count()) * 100

            # Quality Rating Average
            quality_ratings = completed_orders.aggregate(Avg('quality_rating'))['quality_rating__avg'] or 0
            vendor.quality_rating_avg = quality_ratings

            # Average Response Time
            response_times = completed_orders.annotate(
                response_duration=F('acknowledgment_date') - F('issue_date')
            ).aggregate(Avg('response_duration'))['response_duration__avg'] or 0
            vendor.average_response_time = response_times.total_seconds() if response_times else 0

            # Fulfillment Rate
            successful_orders = completed_orders.count()
            total_orders = PurchaseOrder.objects.filter(vendor=vendor).count()
            vendor.fulfillment_rate = (successful_orders / total_orders) * 100

            vendor.save()

class HistoricalPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HistoricalPerformance.objects.all()
    serializer_class = HistoricalPerformanceSerializer
