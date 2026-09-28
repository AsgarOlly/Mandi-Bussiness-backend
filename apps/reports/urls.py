from django.urls import path
from .views import dashboard_summary, daily_sales_report, profit_loss_report

urlpatterns = [
    path('dashboard/', dashboard_summary, name='report_dashboard'),
    path('daily-sales/', daily_sales_report, name='report_daily_sales'),
    path('profit-loss/', profit_loss_report, name='report_profit_loss'),
]
