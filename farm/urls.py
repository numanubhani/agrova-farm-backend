from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('customers', views.CustomerViewSet, basename='customer')
router.register('expenses', views.ExpenseViewSet, basename='expense')
router.register('payments', views.PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    path('settings/', views.farm_settings),
    path('deliveries/', views.deliveries_for_date),
    path('production/', views.production_for_date),
    path('production/recent/', views.production_recent),
    path('dashboard/', views.dashboard),
    path('bills/', views.bills),
    path('bills/<int:customer_id>/receipt/', views.receipt),
    path('reports/', views.reports),
    path('reports/export/', views.reports_export),
    path('reset-demo/', views.reset_demo),
    path('clear-all/', views.clear_all),
]
