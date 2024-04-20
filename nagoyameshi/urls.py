from django.contrib import admin
from django.urls import path
from nagoyameshi import views
from django.conf.urls import include #includeのインポート
from django.conf import settings
from django.conf.urls.static import static
from nagoyameshi-v1 import views

handler500 = views.my_customized_server_error

urlpatterns = [
    path('admin/', admin.site.urls),
    path('top/', views.top_view, name='top'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('cancel_account/', views.cancel_account, name='cancel_account'),
    path('mypage/', views.display_mypage, name='mypage'),
    path('user_info/', views.user_info, name='user_info'),
    path('update/', views.user_update, name='update'),
    path('change_password/', views.change_password, name='change_password'),
    path('list/', views.RestaurantListView.as_view(), name='list'),
    path('restaurant_detail/<int:pk>', views.restaurant_detail, name='restaurant_detail'),
    path('myfavorite/', views.favorite, name='myfavorite'),
    path('list_favorite/', views.list_favorite, name='list_favorite'),
    path('create_review/<int:pk>', views.create_review, name='create_review'),
    path('list_review/<int:pk>', views.list_review, name='list_review'),
    path('review_detail/<int:pk>', views.review_detail, name='review_detail'),
    path('mygood/', views.good, name='mygood'),
    path('reservation/<int:pk>/<int:year>/<int:month>/<int:day>/', views.reserve, name='reservation'),
    path('create_reserve/<int:pk>/<str:date>/<str:time>', views.create_reserve, name='create_reserve'),
    path('list_reservation/', views.list_reservation, name='list_reservation'),
    path('cancel_reservation/<int:restaurant_id>/<int:reservation_id>/', views.cancel_reservation, name='cancel_reservation'),
    path('access_history/', views.access_history, name='access_history'),
    path('admin_top/', views.admin_top_view, name='admin_top'),
    path('create_restaurant/', views.create_restaurant, name='create_restaurant'),
    path('list_managed_restaurant/', views.list_managed_restaurant, name='list_managed_restaurant'),
    path('update_restaurant/<int:restaurant_id>', views.update_restaurant, name='update_restaurant'),
    path('delete_restaurant/<int:restaurant_id>', views.delete_restaurant, name='delete_restaurant'),
    path('list_categories/', views.list_categories, name='list_categories'),
    path('create_category', views.create_category, name='create_category'),
    path('list_managed_restaurant_review/<int:restaurant_id>', views.list_managed_restaurant_review, name='list_managed_restaurant_review'),
    path('list_managed_restaurant_reserve/<int:restaurant_id>', views.list_managed_restaurant_reserve, name='list_managed_restaurant_reserve'),
    path('list_managed_account/', views.list_managed_account, name='list_managed_account'),
    path('download_as_csv/', views.download_as_csv, name='download_as_csv'),
    path('download_accounts_info/', views.download_accounts_info, name='download_accounts_info'),
    path('account_search/', views.account_search, name='account_search'),
    path('confirm_subscribe/', views.confirm_subscribe, name='confirm_subscribe'),
    path('create_checkout_session/<int:pk>/', views.create_checkout_session, name='create_checkout_session'),
    path('pay_success/', views.paysuccess, name='pay_success'),
    path('pay_cancel/', views.paycancel, name='pay_cancel'),
    path('webhook/', views.stripe_webhook, name='webhook'),
    path('confirm_cancel_subscribe/', views.confirm_cancel_subscribe, name='confirm_cancel_subscribe'),
    path('cancel_subscription_session/', views.cancel_subscription_session, name='cancel_subscription_session'),
    path('privacy_policy/', views.privacy_policy_view, name='privacy_policy'),
    path('about/', views.about_view, name='about'),
    path('uriage', views.uriage_view, name='uriage'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)