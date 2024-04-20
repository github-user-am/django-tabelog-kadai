from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from . import forms
from .forms import CreateRestaurantForm
from django.views.generic import TemplateView, ListView, FormView, CreateView
from .models import CustomUser, Restaurant, Category, Favorite, Review, Good, Reservation, AccessHistory, Subscriber, SubscriptionProduct, SubscriptionPrice, Transaction
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, Http404, HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.db import connection
from django.conf import settings
import datetime
import csv
import io
import urllib
import stripe
import calendar

# Create your views here.

### Stripe ###
# STRIPEのシークレットキー
stripe.api_key = settings.STRIPE_SECRET_KEY
# WEBHOOKのシークレットキー
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

### トップページ ###
def top_view(request):
    if request.method == 'GET':
        # base表示用カテゴリ
        categories = Category.objects.all()
        # レストランを新着順で取得
        restaurants_new = Restaurant.objects.filter().order_by('-create_at')[:4]
        # レビュー高評価順
        reviews_highscore = Review.objects.values('restaurant_id').annotate(
            average=Avg('score'),
            ).order_by('average').reverse()[:4]

        highscore_restaurant_list = []
        for review in reviews_highscore:
            qry_set = Restaurant.objects.filter(id=review['restaurant_id'])

            # レビュー数、スコア、カテゴリ名を取り出して辞書に追加する
            score = qry_set[0].avg_score()
            star_score = qry_set[0].avg_star_icon()
            review_count = qry_set[0].review_count()

            cat_qry_sets = qry_set[0].get_category_name()
            cat_list = []
            for cat_qry_set in cat_qry_sets:
                cat_name = cat_qry_set.category_name
                cat_list.append(cat_name)

            # クエリセットをリスト化してスコアとカテゴリの情報を追加する
            restaurant_record_list = list(qry_set.values())
            restaurant_record_list[0]['score'] = score
            restaurant_record_list[0]['star_score'] = star_score
            restaurant_record_list[0]['review_count'] = review_count
            restaurant_record_list[0]['res_categories'] = cat_list

            # 配列に入れる
            highscore_restaurant_list.append(restaurant_record_list)
        
        # レビューが多い順
        reviews_many = Review.objects.values('restaurant_id').annotate(
            count = Count('restaurant_id',)
        ).order_by('count').reverse()[:4]

        many_review_restaurant_list = []
        for review_many in reviews_many:
            res_qry_set = Restaurant.objects.filter(id=review_many['restaurant_id'])

            # レビュー数、スコア、カテゴリ名を取り出して辞書に追加する
            score = res_qry_set[0].avg_score()
            star_score = res_qry_set[0].avg_star_icon()
            review_count = res_qry_set[0].review_count()

            cat_qry_sets = res_qry_set[0].get_category_name()
            cat_list = []
            for cat_qry_set in cat_qry_sets:
                cat_name = cat_qry_set.category_name
                cat_list.append(cat_name)

            # クエリセットをリスト化してレビュー数、スコア、カテゴリの情報を追加する
            many_review_record_list = list(res_qry_set.values())
            many_review_record_list[0]['score'] = score
            many_review_record_list[0]['star_score'] = star_score
            many_review_record_list[0]['review_count'] = review_count
            many_review_record_list[0]['res_categories'] = cat_list
        
            # 配列に入れる
            many_review_restaurant_list.append(many_review_record_list)
        
        return render(request, 'top.html', context={
            'categories': categories,
            'restaurants_new': restaurants_new,
            'highscore_restaurant_list': highscore_restaurant_list,
            'many_review_restaurant_list': many_review_restaurant_list,
        })
    else:
        raise Http404

### プライバシーポリシー画面 ###
def privacy_policy_view(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    if request.method == 'GET':
        return render(request, 'privacy_policy.html', context={
            'categories': categories,
        })
    else:
        raise Http404

### About画面 ###
def about_view(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    if request.method == 'GET':
        return render(request, 'about.html', context={
            'categories': categories,
        })
    else:
        raise Http404

### 会員登録 ###
def signup(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    # フォーム
    form = forms.SignupForm(request.POST or None)
    if form.is_valid():
        email = form.cleaned_data['email']
        nickname = form.cleaned_data['nickname']
        password = form.cleaned_data['password']
        try:
            user = CustomUser.objects.create_user(email=email, nickname=nickname, password=password)
            user.save()
            return redirect('top')
        except ValidationError as e:
            form.add_error('password', e)
    return render(request, 'signup.html', context={
        'form': form,
        'categories': categories,
    })

### ログイン ###
def user_login(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    # フォーム
    form = forms.LoginForm(request.POST or None)
    if form.is_valid():
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        user = authenticate(email=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('/top/')
        else:
            return render(request, 'login.html', context={
                'form': form,
                'message': '*メールアドレスかパスワードが間違っています'
            })
    return render(request, 'login.html', context={
        'form': form,
        'categories': categories,
    })

### ログアウト ###
@login_required
def user_logout(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    logout(request)
    
    return render(request, 'logout.html', context={
        'categories': categories,
    })

### マイページを表示（ログインが必要） ###
@login_required
def display_mypage(request):
    if request.method == 'GET':
        # base表示用カテゴリ
        categories = Category.objects.all()
        # 会員種別の判定
        if Subscriber.objects.filter(user_id=request.user.id):
            is_subscriber = True
        else:
            is_subscriber = False
        return render(request, 'mypage.html', context={
            'categories': categories,
            'is_subscriber': is_subscriber,
        })
    else:
        raise Http404

### 会員情報を表示（ログインが必要） ###
@login_required
def user_info(request):
    if request.method == 'GET':
        # base表示用カテゴリ
        categories = Category.objects.all()
        user = CustomUser.objects.get(id=request.user.id)

        if user:
            return render(request, 'user_info.html', context={
                'categories': categories,
                'user': user,
            })
    else:
        raise Http404

### 会員情報更新（ログインが必要） ###
@login_required
def user_update(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    user = CustomUser.objects.get(id=request.user.id)
    form = forms.UpdateForm(instance=user)
    if request.method == 'POST':
        form = forms.UpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return render(request, 'success.html', context={
                'categories': categories,
                'message': 'ユーザー情報が更新されました。',
                'url': reverse('user_info'),
                'text': '会員情報',
            })
    else:
        return render(request, 'update.html', context={
            'form': form,
            'categories': categories,
        })

### パスワード変更（ログインが必要） ###
@login_required
def change_password(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    user = CustomUser.objects.get(id=request.user.id)
    form = forms.PasswordChangeForm(user.email)
    if request.method == 'POST':
        form = forms.PasswordChangeForm(user.email, request.POST)
        if form.is_valid():
            password = form.cleaned_data['new_password']
            user.set_password(password)
            user.save()
            return render(request, 'change_password.html', context={
                'message': 'パスワードが変更されました',
                'categories': categories,
            })
    return render(request, 'change_password.html', context={
        'form': form,
        'categories': categories,
    })

### 店舗一覧と検索（会員登録不要） ###
class RestaurantListView(ListView):
    template_name = 'list.html'
    queryset = Restaurant.objects.all().order_by('-create_at')
    model = Restaurant
    paginate_by = 10

    def get_queryset(self):
        context_object_name = 'restaurant_list'
        queryset = Restaurant.objects.all().order_by('-create_at')
        keyword = self.request.GET.get('keyword')
        area = self.request.GET.get('area')
        category_id = self.request.GET.get('category_id')

        # keywordが入力されていたら、店舗名か店舗説明にキーワードが入っている場合をフィルタ
        if keyword:
            queryset = queryset.filter(
                (Q(restaurant_name__icontains=keyword)|Q(description__icontains=keyword))
                )
        
        # areaが入力されていたら、住所でフィルタ
        if area:
            queryset = queryset.filter(Q(address__icontains=area))

        # categoryが選択されたら、カテゴリでフィルタ
        if category_id:
            queryset = queryset.filter(restaurant_category=category_id)
        
        result_num = queryset.count()
        
        # Paginator
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page')
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        # テンプレートに変数を渡す
        messages.add_message(self.request, messages.INFO, queryset.count(), result_num)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

### 店舗詳細（会員登録不要） ###
def restaurant_detail(request, pk):
    if request.method == 'GET':
        # base表示用カテゴリ
        categories = Category.objects.all()
        # アクセスした日の年月日（予約用）
        today = datetime.date.today()
        # レストランのレビューを新着順で5つ抽出する
        restaurant_reviews = Review.objects.filter(restaurant_id=pk).order_by('-create_at')[:5]
        # restaurant_idがpkと一致するレストラン
        restaurant = Restaurant.objects.get(id=pk)       
        # ログインしているかどうかをチェック
        if request.user.is_authenticated:
            is_user_logged_in = True
            # urlとuser・restaurantオブジェクトを取得してAccressHistoryモデルに格納(閲覧履歴用)
            url = request.path
            user = CustomUser.objects.get(id=request.user.id)
            AccessHistory.objects.create(url=url, user=user, restaurant=restaurant)
            # 有料会員かどうかチェック
            if Subscriber.objects.filter(user_id=request.user.id):
                is_user_subscribed = True
                # 既にお気に入り済みかチェック
                if Favorite.objects.filter(restaurant_id=pk, user_id=request.user.id):
                    is_user_liked = True
                else:
                    is_user_liked = False
                # restaurant、is_user_logged_in、is_user_subscribed、is_user_likedの情報をcontextで返す
                return render(request, 'restaurant_detail.html', context={
                    'categories': categories,
                    'restaurant': restaurant,
                    'restaurant_reviews': restaurant_reviews,
                    'is_user_logged_in': is_user_logged_in,
                    'is_user_subscribed': is_user_subscribed,
                    'is_user_liked': is_user_liked,
                    'today': today,
                })
            else:
                is_user_subscribed = False
                # restaurant、is_user_logged_in、is_user_subscribedを返す
                return render(request, 'restaurant_detail.html', context={
                    'categories': categories,
                    'restaurant': restaurant,
                    'restaurant_reviews': restaurant_reviews,
                    'is_user_logged_in': is_user_logged_in,
                    'is_user_subscribed': is_user_subscribed,
                    'today': today,
                })
        # ログインしていなければ、restaurant、is_user_loggedinを返す
        else:
            is_user_logged_in = False
            return render(request, 'restaurant_detail.html', context={
                'categories': categories,
                'restaurant': restaurant,
                'restaurant_reviews': restaurant_reviews,
                'is_user_logged_in': is_user_logged_in,
                'today': today,
            })
    else:
        # POSTの場合
        return favorite(request)

### お気に入り登録（有料会員専用） ###
@login_required
def favorite(request):
    # 有料会員かどうかチェック
    if Subscriber.objects.filter(user_id=request.user.id):
        restaurant_id = request.POST.get('restaurant_id') #POSTリクエストで与えられたrestaurantのidを取得
        context = {
            'user_id': f'{ request.user.id }'
        }
        # Restaurantモデルからidがrestaurant_idであるものを取り出す
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        # Favoriteテーブルからrestaurantとuser_idの紐づけが無いかチェック
        favorite = Favorite.objects.filter(restaurant_id=restaurant_id, user_id=request.user.id)

        if favorite.exists():
            favorite.delete()
            # context['method'] = 'delete'
            # method = 'delete'
            return JsonResponse({'method':'delete'})
        else:
            Favorite.objects.create(restaurant_id=restaurant_id, user_id=request.user.id)
            # context['method'] = 'create'
            # method = 'create'
            return JsonResponse({'method':'create'})
    else:
        raise Http404

### お気に入り一覧表示（有料会員専用） ###
@login_required
def list_favorite(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    # 有料会員かどうかチェック
    if Subscriber.objects.filter(user_id=request.user.id):
        user = CustomUser.objects.get(id=request.user.id)
        # Favorite modelからuser_idが一致するクエリセットを抽出
        fav_qry_sets = Favorite.objects.filter(user_id=request.user.id)
        # お気に入りがある場合
        if fav_qry_sets:
        # dict型にする
            favorite_lists = list(fav_qry_sets.values())
            
            res_favorite_list = []
            for favorite in favorite_lists:
                fav_create_at = favorite['create_at']
                res_qry_set = Restaurant.objects.filter(id=favorite['restaurant_id'])
                fav_record_list = list(res_qry_set.values())
                fav_record_list[0]['fav_create_at'] = fav_create_at
                res_favorite_list.append(fav_record_list)
            
            # Paginator
            paginator = Paginator(res_favorite_list, 10)
            page_number = request.GET.get('page')
            try:
                page_obj = paginator.get_page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.get_page(1)
            except EmptyPage:
                page_obj = paginator.get_page(paginator.num_pages)

            return render(request, 'list_favorite.html', context={
                'categories': categories,
                'res_favorite_list': page_obj.object_list,
                'page_obj': page_obj,
            })

        # お気に入りがない場合
        else:
            return render(request, 'list_favorite.html', context={
                'categories': categories,
                'message': 'お気に入りはありません。',
            })
    else:
        # 有料会員でない場合は有料会員登録画面を表示
        return render(request, 'confirm_subscribe.html', context={
            'categories': categories,
        })

### レビュー投稿（有料会員専用） ###
@login_required
def create_review(request, pk):
    # base表示用カテゴリ
    categories = Category.objects.all()
    # 有料会員かどうかチェック
    if Subscriber.objects.filter(user_id=request.user.id):
        # 対象のレストランと投稿ユーザーを取得
        restaurant = Restaurant.objects.get(id=pk)
        user = CustomUser.objects.get(id=request.user.id)
        # 既に同じレストラン・ユーザーの組み合わせで投稿があるかどうか
        review = Review.objects.filter(restaurant_id=restaurant.id, user_id=user.id)
        try:
            review = review.__dict__
            review_id = review['id']
        except:
            review_id = None
        form = forms.ReviewForm(request.POST or review)
        if request.method == "POST":
            if form.is_valid():
                restaurant_id = restaurant.id
                user_id = user.id
                review_title = form.cleaned_data['review_title']
                review_comment = form.cleaned_data['review_comment']
                score = form.cleaned_data['score']

                review = Review.objects.update_or_create(
                    id = review_id,
                    defaults = {
                        'restaurant_id': restaurant_id,
                        'user_id': user_id,
                        'review_title': review_title,
                        'review_comment': review_comment,
                        'score': score,
                    }
                )
                # review.save()
                return redirect('restaurant_detail', pk=restaurant_id)
        return render(request, 'create_review.html', context={
                'form': form,
                'categories': categories,
            })
    else:
        # 有料会員でない場合は有料会員登録画面を表示
        return render(request, 'confirm_subscribe.html', context={
            'categories': categories,
        })

### レビューの一覧表示（会員登録不要） ###
def list_review(request, pk):
    if request.method == 'GET':
        # base表示用カテゴリ
        categories = Category.objects.all()
        # 対象のレストランのレビューを全権取得
        restaurant_reviews = Review.objects.filter(restaurant_id=pk).order_by('id')
        
        # conditionの値によりフィルタ
        condition = request.GET.get('condition')
        # 評価が高い
        if condition == 'score':
            restaurant_reviews = restaurant_reviews.order_by('-score')
        # 投稿が新しい
        elif condition == 'new':
            restaurant_reviews = restaurant_reviews.order_by('-create_at')
        else:
            restaurant_reviews = restaurant_reviews
        
        # レストランがあれば
        if restaurant_reviews:
            # Paginator
            paginator = Paginator(restaurant_reviews, 5)
            page_number = request.GET.get('page')
            try:
                page_obj = paginator.get_page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.get_page(1)
            except EmptyPage:
                page_obj = paginator.get_page(paginator.num_pages)

            return render(request, 'list_review.html', context={
                'categories': categories,
                'restaurant_reviews': page_obj.object_list,
                'page_obj': page_obj,
            })
        else:
            return render(request, 'list_review.html', context={
                'message': 'レビューはまだありません。'
            })
    else:
        raise Http404

### レビューの詳細画面（無料会員＋有料会員） ###
@login_required
def review_detail(request, pk):
    if request.method == 'GET':
        # base表示用カテゴリ
        categories = Category.objects.all()
        # idがpkと一致するレビューを取得
        review = Review.objects.get(id=pk)
        # ユーザーが既にレビューをGood済みかチェック
        if Good.objects.filter(review_id=pk, user_id=request.user.id):
            is_user_good = True
        else:
            is_user_good = False
        # review、is_user_goodの情報をcontextで返す
        return render(request, 'review_detail.html', context={
            'categories': categories,
            'review': review,
            'is_user_good': is_user_good
        })
    else:
        # POSTの場合
        return Good(request)

### レビューの評価ボタン（無料会員＋有料会員） ###
@login_required
def good(request):
    review_id = request.POST.get('review_id') #POSTリクエストで与えられたreviewのidを取得
    context = {
        'user_id': f'{ request.user.id }'
    }
    # Reviewモデルからidがreview_idであるものを取り出す
    review = get_object_or_404(Review, id=review_id)
    # Goodテーブルからreviewとuser_idの紐づけが無いかチェック
    good = Good.objects.filter(review_id=review_id, user_id=request.user.id)

    if good.exists():
        good.delete()
        # context['method'] = 'delete'
        # method = 'delete'
        return JsonResponse({'method':'delete'})
    else:
        Good.objects.create(review_id=review_id, user_id=request.user.id)
        # context['method'] = 'create'
        # method = 'create'
        return JsonResponse({'method':'create'})

### 予約カレンダーの表示（有料会員専用） ###
# 予約ページにジャンプさせるための関数を定義
@login_required
def reserve(request, **kwargs):
    # base表示用カテゴリ
    categories = Category.objects.all()
    # 有料会員かどうかチェック
    if Subscriber.objects.filter(user_id=request.user.id):
        if request.method == 'GET':

            context = {}

            # 本日の日付を取得
            today = datetime.date.today()
            # 引数からレストランのidと日付を取得
            restaurant_id = kwargs['pk']
            year = kwargs['year']
            month = kwargs['month']
            day = kwargs['day']

            # 起点日の設定
            # 日付が指定されていればその日付を起点とするが、なければアクセス日時をもとに設定
            if year and month and day:
                base_date = datetime.date(year=year, month=month, day=day)
            else:
                base_date = today

            print(f'base_date:{base_date}')

            # 「日」のデータを動的に生成する
            # range(7)は日付を示すため、ひと月分を取得したいのであればその月の最終日をrangeに入れれば良い
            # 1ページに見せる量は1週間が丁度良いと思いますのでそのままでも良いと思います
            # ちなみに下記は内包表記と呼ばれる記法で表現しています
            days = [base_date + datetime.timedelta(days=day) for day in range(7)]

            print(f'days:{days}')

            # カレンダーの開始日を指定
            start_day = days[0]

            # カレンダーの最終日を指定
            end_day = days[-1]

            # 9時から17時まで1時間刻み、1週間分の、値がTrueなカレンダーを作る
            # カレンダーのデータを生成する
            # hourが9時～17時(9を含め、17までの計18個)として設定し、その日付に「○」を設定したいのでTrueを持たせておく
            # この時間については各店舗ごとに設定を変えられるようにしたいところであるが、実装最優先で行きたいので
            # 決め打ちでも良いと思われます
            calendar = {}

            # 開店時間と閉店時間を取得
            restaurant = Restaurant.objects.get(id=restaurant_id)
            res_opening_time = restaurant.opening
            res_closing_time = restaurant.closing
            
            # 定休日を取得（月曜日が0で日曜日が6）
            regular_holiday = restaurant.regular_holiday
            if regular_holiday == 'monday':
                regular_holiday = 0
            elif regular_holiday == 'tuesday':
                regular_holiday = 1
            elif regular_holiday == 'wednesday':
                regular_holiday = 2
            elif regular_holiday == 'thursday':
                regular_holiday = 3
            elif regular_holiday == 'friday':
                regular_holiday = 4
            elif regular_holiday == 'saturday':
                regular_holiday = 5
            elif regular_holiday == 'sunday':
                regular_holiday = 6
            
            # 席数を取得
            max_seat_num = restaurant.seat_number
            print(f'max_seat_num:{max_seat_num}')

            # 時間の計算のためにdatetime.timeオブジェクトをdatetimeオブジェクトに変換
            res_closing_time = datetime.datetime.combine(today, res_closing_time)
            res_opening_time = datetime.datetime.combine(today, res_opening_time)

            # 範囲指定のため、閉店時間に1時間+する
            additional_hour = datetime.timedelta(hours=1)
            res_closing_time = res_closing_time + additional_hour

            # datetimeオブジェクトだとrangeに指定できない?ので、時間をintに変換
            opening = res_opening_time.hour
            closing = res_closing_time.hour

            # for hour in range(9, 18):
            for hour in range(opening, closing):

                # 1日ごとの状況にTrueを入れる。定休日にはFalseを入れる
                row = {}
                for day in days:
                    if day.weekday() == regular_holiday:
                        row[day] = [False, 0]
                    else:
                        row[day] = [True, 0]

                # カレンダーのデータのキーを時間として上記で日ごとに設定したTrueデータを入れておく
                calendar[hour] = row

            # カレンダーの開始時刻、最終時刻を設定しておく
            # 今回の例でいうと9時、17時となる
            start_time = datetime.datetime.combine(start_day,datetime.time(hour=opening, minute=0, second=0))
            end_time = datetime.datetime.combine(end_day, datetime.time(hour=closing-1,minute=0, second=0))

            # 各店舗が保持するスケジュール(予約情報のモデル)から、すべての予約情報を取得して、
            # 開始時刻～最終時刻に収まるデータを取得する
            for reservation in Reservation.objects.filter(restaurant_id=restaurant_id).exclude(Q(reservation_start__gt=end_time) | Q(reservation_end__lt=start_time)):

                # 繰り返し中に取得できた開始時刻情報を取得する
                local_dt = timezone.localtime(reservation.reservation_start)
                print(f'local_dt:{local_dt}')

                # 上記で取得した開始時刻をbooking_dateに設定
                booking_date = local_dt.date()
                print(f'booking_date:{booking_date}')

                # 何時間の予約かをbooking_hourに設定
                booking_hour = local_dt.hour
                print(f'booking_hour:{booking_hour}')

                # カレンダーデータの中で日付と時間帯が一致する部分があれば
                if booking_hour in calendar and booking_date in calendar[booking_hour]:
                    # 予約済み(もう予約できない)としてFalseを設定
                    # 必要に応じて、何個予約があるか、などで分けてもいいかもしれないですね
                    # 残り2,3などで△となる…みたいな
                    # その場合はTrue/Falseでは足りないので直接文字列指定でもよいです。
                    calendar[booking_hour][booking_date][1] += 1

            # テンプレートに渡すためのデータをまとめる
            context['calendar'] = calendar
            context['days'] = days
            context['start_day'] = start_day
            context['end_day'] = end_day
            context['before'] = days[0] - datetime.timedelta(days=7) # 一週間前の日付を設定しておく
            context['next'] = days[-1] + datetime.timedelta(days=1)  # 一週間後の日付を設定しておく
            context['today'] = today
            context['restaurant'] = restaurant
            context['max_seat_num'] = max_seat_num
            return render(request, 'reservation.html', context)
        else:
            raise Http404
    else:
        # 有料会員でない場合は有料会員登録画面を表示
        return render(request, 'confirm_subscribe.html', context={
            'categories': categories,
        })

### 予約（有料会員専用） ###
@login_required
def create_reserve(request, pk, date, time):
    # base表示用カテゴリ
    categories = Category.objects.all()
    if Subscriber.objects.filter(user_id=request.user.id):
        # 対象のレストランと予約ユーザー名を取得
        restaurant = Restaurant.objects.get(id=pk)
        user = CustomUser.objects.get(id=request.user.id)
        nickname = user.get_nickname
        
        # 予約日時をstr型からdate型やdatetimeに変換する
        str_datetime = date + ' ' + time + ':00:00'
        # 予約日
        date_time = datetime.datetime.strptime(str_datetime, '%Y-%m-%d %H:%M:%S')
        reservation_date = datetime.date(date_time.year, date_time.month, date_time.day)
        # 予約開始時間
        reservation_start = datetime.datetime.strptime(str_datetime, '%Y-%m-%d %H:%M:%S')
        # 予約終了時間（開始時間+1時間）
        additional_hour = datetime.timedelta(hours=1)
        reservation_end = reservation_start + additional_hour

        # 同じ日時、同じユーザー、同じレストランで予約があるかどうか
        reservation = Reservation.objects.filter(reservation_date=reservation_date, reservation_start=reservation_start, restaurant_id=restaurant.id, user_id=user.id)
        if reservation:
            today = datetime.date.today()
            year = today.year
            month = today.month
            day = today.day
            return render(request, 'cancel.html', context={
                'categories': categories,
                'message': '既に予約があります。',
                'url': reverse('reservation', kwargs={'pk': restaurant.id, 'year': year, 'month': month, 'day': day}),
                'text': '予約カレンダー',
            })

        # 予約人数を入れるフォーム
        form = forms.ReservationForm(request.POST or None)
        if form.is_valid():
            number_of_people = form.cleaned_data['number_of_people']
            if number_of_people != '0':
                reservation = Reservation.objects.create(
                    reservation_date=reservation_date, 
                    reservation_start=reservation_start,
                    reservation_end=reservation_end,
                    number_of_people=number_of_people,
                    restaurant_id=restaurant.id,
                    user_id=user.id
                )
                reservation.save()
                return render(request, 'success.html', context={
                    'categories': categories,
                    'message': '予約が完了しました!',
                    'url': reverse('list_reservation'),
                    'text': '予約一覧',
                })
            else:
                return render(request, 'reserve_restaurant.html', context={
                    'categories': categories,
                    'form': form,
                    'restaurant': restaurant,
                    'nickname': nickname,
                    'reservation_start': reservation_start,
                    'reservation_end': reservation_end,
                    'message': '予約人数を設定してください'
                })
        # requestがGETの場合
        return render(request, 'reserve_restaurant.html', context={
            'categories': categories,
            'form': form,
            'restaurant': restaurant,
            'nickname': nickname,
            'reservation_start': reservation_start,
            'reservation_end': reservation_end,
        })
    else:
        # 有料会員でない場合は有料会員登録画面を表示
        return render(request, 'confirm_subscribe.html', context={
            'categories': categories,
        })

### 予約一覧（有料会員専用） ###
@login_required
def list_reservation(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    # 対象のユーザーを取得
    user = CustomUser.objects.get(id=request.user.id)
    # 有料会員かどうかチェック
    if Subscriber.objects.filter(user_id=request.user.id):
        # Reservation modelからuser_idが一致するクエリセットを抽出
        rsvd_qry_sets = Reservation.objects.filter(user_id=request.user.id).order_by('-reservation_start')
        # ログインユーザーで予約がある場合
        if rsvd_qry_sets:
            # dict型にする
            rsvd_lists = list(rsvd_qry_sets.values())
            print(rsvd_lists)
            rsvd_res_list = []
            for rsvd in rsvd_lists:
                # 予約内容を取得
                reservation_id = rsvd['id']
                reservation_start = rsvd['reservation_start']
                reservation_end = rsvd['reservation_end']
                number_of_people = rsvd['number_of_people']

                res_qry_set = Restaurant.objects.filter(id=rsvd['restaurant_id'])
                res_record_list = list(res_qry_set.values())
                res_record_list[0]['reservation_id'] = reservation_id
                res_record_list[0]['reservation_start'] = reservation_start
                res_record_list[0]['reservation_end'] = reservation_end
                res_record_list[0]['number_of_people'] = number_of_people
                rsvd_res_list.append(res_record_list)
            
            # Paginator
            paginator = Paginator(rsvd_res_list, 10)
            page_number = request.GET.get('page')
            try:
                page_obj = paginator.get_page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.get_page(1)
            except EmptyPage:
                page_obj = paginator.get_page(paginator.num_pages)

            return render(request, 'list_reservation.html', context={
                'categories': categories,
                'rsvd_res_list': page_obj.object_list,
                'page_obj': page_obj,
            })
        else:
            # 予約がない場合
            return render(request, 'list_reservation.html', context={
                'categories': categories,
                'message': '予約はありません。',
            })
    else:
        # 有料会員でない場合は有料会員登録画面を表示
        return render(request, 'confirm_subscribe.html', context={
            'categories': categories,
        })

### 予約キャンセル（有料会員専用） ###
@login_required
def cancel_reservation(request, restaurant_id, reservation_id):
    # base表示用カテゴリ
    categories = Category.objects.all()
    # ユーザー、レストラン、予約を取得
    user = CustomUser.objects.get(id=request.user.id)
    # 有料会員かどうかチェック
    if Subscriber.objects.filter(user_id=request.user.id):
        restaurant = Restaurant.objects.get(id=restaurant_id)
        reservation = Reservation.objects.get(id=reservation_id)
        if request.method == 'POST':
            reservation.delete()
            return render(request, 'success.html', context={
                'categories': categories,
                'message': '予約をキャンセルしました!',
                'url': reverse('list_reservation'),
                'text': '予約一覧',
            })
        else:
            return render(request, 'cancel_reservation.html', context={
                    'categories': categories,
                    'restaurant': restaurant,
                    'reservation': reservation,
                })
    else:
        # 有料会員でない場合は有料会員登録画面を表示
        return render(request, 'confirm_subscribe.html', context={
            'categories': categories,
        })

### 閲覧履歴（無料会員＋有料会員） ###
@login_required
def access_history(request):
    if request.method == 'GET':
        # base表示用カテゴリ
        categories = Category.objects.all()
        # ログインユーザーを取得
        user = CustomUser.objects.get(id=request.user.id)
        # ログインユーザーのアクセス履歴のオブジェクト直近20件を取得
        his_qry_set = AccessHistory.objects.filter(user=user).order_by('-time').distinct()[:20]

        if his_qry_set:
            # クエリセットをリスト化する
            histories_list = list(his_qry_set.values())
            for histories in histories_list:
                restaurant = Restaurant.objects.get(id=histories['restaurant_id'])
                # レストラン名を取り出してアクセス履歴リストに追加
                histories['restaurant_name'] = restaurant.restaurant_name
                
            return render(request, 'access_history.html', context={
                'categories': categories,
                'histories_list': histories_list,
            })
        else:
            return render(request, 'access_history.html', context={
                'categories': categories,
                'message': '閲覧履歴はありません'
            })
    else:
        raise Http404

### 管理者ページトップ（管理者ユーザー専用） ###
@login_required
def admin_top_view(request):
    if request.method == 'GET':
        # base表示用カテゴリ
        categories = Category.objects.all()
        # 管理者ユーザーかどうかチェック
        user = CustomUser.objects.get(id=request.user.id)
        if user.is_superuser or user.is_admin:
            return render(request, 'admin_top.html', context={
                'user': user,
            })
        else:
            return render(request, 'cancel.html', context={
            'message': '管理者ユーザー専用ページのため、アクセスできません。',
            'url': reverse('top'),
            'text': 'TOP',
            'categories': categories,
            })
    else:
        raise Http404

### 店舗新規作成（店舗管理者専用） ###
@login_required
def create_restaurant(request):
    user = CustomUser.objects.get(id=request.user.id)
    if user.is_superuser or user.is_admin:
        if request.method == 'POST':
            restaurant_admin_id = request.user.id
            form = CreateRestaurantForm(request.POST, request.FILES)
            if form.is_valid():
                restaurant_category = form.cleaned_data.get('restaurant_category') # クエリセット
                print(restaurant_category)
                restaurant_name = form.cleaned_data.get('restaurant_name')
                restaurant_image = request.FILES['restaurant_image']
                description = form.cleaned_data.get('description')
                postal_code = form.cleaned_data.get('postal_code')
                address = form.cleaned_data.get('address')
                opening = form.cleaned_data.get('opening')
                closing = form.cleaned_data.get('closing')
                regular_holiday = form.cleaned_data.get('regular_holiday')
                seat_number = form.cleaned_data.get('seat_number')
                phone_number = form.cleaned_data.get('phone_number')

                obj = Restaurant.objects.create(
                                    #  restaurant_category = restaurant_category,
                                    restaurant_name = restaurant_name,
                                    restaurant_image = restaurant_image,
                                    description = description,
                                    postal_code = postal_code,
                                    address = address,
                                    opening = opening,
                                    closing = closing,
                                    regular_holiday = regular_holiday,
                                    seat_number = seat_number,
                                    phone_number = phone_number,
                                    restaurant_admin_id = restaurant_admin_id,
                                    )

                # カテゴリを設定
                categories = list(restaurant_category.values()) # クエリセットをリスト化
                for i in range(0, len(categories)):
                    category_id = categories[i]['id']
                    obj.restaurant_category.add(category_id)
                return render(request, 'admin_success.html', context={
                    'message': '店舗が作成されました!',
                    'url': reverse('list_managed_restaurant'),
                    'text': '管理店舗一覧',
                })
        else:
            form = CreateRestaurantForm()
            return render(request, 'create_restaurant.html', context={
                'form': form,
            })
    else:
        # 店舗管理者でなければアクセス拒否
        return render(request, 'access_denied.html', context={
                'message': 'このページは管理者専用です。',
                'url': reverse('admin_top'),
                'text': '管理者トップ',
            })

### 管理店舗一覧表示（店舗管理者専用） ###
@login_required
def list_managed_restaurant(request):
    if request.method == 'GET':
        # ユーザーを取得して、ユーザーがいるかチェック
        user = CustomUser.objects.get(id=request.user.id)
        # userがサイト管理者かチェック
        if user.is_superuser:
            # すべての店舗を取得
            managed_restaurants = Restaurant.objects.all()
            # 店舗があるかチェック
            if managed_restaurants:
                return render(request, 'managed_restaurant.html', context={
                    'managed_restaurants': managed_restaurants,
                })
            else:
                return render(request, 'managed_restaurant.html', context={
                    'message': '店舗が存在しません。',
                })
        # userが店舗管理者かチェック
        elif user.is_admin:
            # userが管理者になっている店舗を取得
            managed_restaurants = Restaurant.objects.filter(restaurant_admin_id=user.id)
            # 店舗があるかチェック
            if managed_restaurants:
                return render(request, 'managed_restaurant.html', context={
                    'managed_restaurants': managed_restaurants,
                })
            else:
                return render(request, 'managed_restaurant.html', context={
                    'message': '店舗が存在しません。',
                })
        else:
            return render(request, 'access_denied.html', context={
                'message': 'このページは店舗管理者専用です。',
                'url': reverse('admin_top'),
                'text': '管理者トップ',
            })
    else:
        raise Http404

### 店舗情報の更新（店舗管理者専用） ###
@login_required
def update_restaurant(request, restaurant_id):
    # ユーザーを取得
    user = CustomUser.objects.get(id=request.user.id)
    # 店舗管理者かどうかチェック
    if user.is_superuser or user.is_admin:
        # 店舗を取得する
        restaurant = Restaurant.objects.get(id=restaurant_id)
        # フォーム
        form = forms.UpdateRestaurantForm(instance=restaurant)
        if request.method == 'POST':
            form = forms.UpdateRestaurantForm(request.POST, instance=restaurant)
            if form.is_valid():
                form.save()
                return render(request, 'admin_success.html', context={
                        'message': '店舗が更新されました!',
                        'url': reverse('list_managed_restaurant'),
                        'text': '管理店舗一覧',
                    })
            else:
                print(form.errors)
        else:
            return render(request, 'update_restaurant.html', context={
                'form': form,
            })
    else:
        return render(request, 'access_denied.html', context={
                'message': 'このページは管理者専用です。',
                'url': reverse('admin_top'),
                'text': '管理者トップ',
            })

### 管理店舗を削除（店舗管理者専用） ###
@login_required
def delete_restaurant(request, restaurant_id):
    if request.method == 'GET':
        user = CustomUser.objects.get(id=request.user.id)
        # 店舗管理者かどうかチェック
        if user.is_superuser or user.is_admin:
            # 店舗を取得
            try:
                restaurant = Restaurant.objects.get(id=restaurant_id)
                # 店舗があれば
                if restaurant:
                    restaurant.delete()
                    return render(request, 'admin_success.html', context={
                        'message': '店舗を削除しました。',
                        'url': reverse('list_managed_restaurant'),
                        'text': '管理店舗一覧',
                    })
            except:
                raise Http404
        else:
            return render(request, 'access_denied.html', context={
                'message': 'このページは管理者専用です。',
                'url': reverse('admin_top'),
                'text': '管理者トップ',
            })
    else:
        raise Http404

### カテゴリの一覧表示（サイト管理者、店舗管理者専用） ###
@login_required
def list_categories(request):
    if request.method == 'GET':
        user = CustomUser.objects.get(id=request.user.id)
        # サイト管理者または店舗管理者かどうかチェック
        if user.is_superuser or user.is_admin:
            # カテゴリを取得
            categories = Category.objects.all()
            # カテゴリがあれば
            if categories:
                return render(request, 'list_categories.html', context={
                    'categories': categories,
                })
            else:
                return render(request, 'list_categories.html', context={
                    'no_category_message': 'カテゴリが見つかりませんでした。',
                })
        else:
            raise Http404
    else:
        raise Http404

### カテゴリの作成（サイト管理者、店舗管理者専用） ###
@login_required
def create_category(request):
    # カテゴリを取得
    categories = Category.objects.all()
    if request.method == 'POST':
        user = CustomUser.objects.get(id=request.user.id)
        # サイト管理者または店舗管理者かどうかチェック
        if user.is_superuser or user.is_admin:
            category_name = request.POST.get('category_name')
            if category_name is not None:
                # 前後のスペースを削除
                category_name = category_name.strip()
                # 既存のカテゴリ名と重複していないかチェック
                existing_cat_name = []
                category_record_list = list(categories.values())
                for category in category_record_list:
                    existing_cat_name.append(category['category_name'])
                if category_name in existing_cat_name:
                    # カテゴリが既にあったら作成しない
                    return render(request, 'list_categories.html', context={
                    'message': 'カテゴリは既に存在します',
                    'categories': categories,
                    }) 
                else:
                    # 有効な文字列になっているかチェック
                    if len(category_name) > 0:
                        Category.objects.create(category_name=category_name)
                        return render(request, 'admin_success.html', context={
                            'message': 'カテゴリを作成しました!',
                            'url': reverse('list_categories'),
                            'text': 'カテゴリ一覧',
                        })
                    else:
                        return render(request, 'list_categories.html', context={
                        'message': 'カテゴリ名を入力してください',
                        'categories': categories,
                        })
            else:
                return render(request, 'list_categories.html', context={
                    'message': 'カテゴリ名を入力してください',
                    'categories': categories,
                })
        else:
            return render(request, 'access_denied.html', context={
                'message': 'このページは管理者専用です。',
                'url': reverse('top'),
                'text': 'TOP',
            })
    else:
        return render(request, 'list_categories.html', context={
            'categories': categories,
        })

### 管理店舗のレビュー一覧（店舗管理者専用） ###
@login_required
def list_managed_restaurant_review(request, restaurant_id):
    # base表示用カテゴリ
    categories = Category.objects.all()
    if request.method == 'GET':
        # ユーザーを取得して、ユーザーがいるかチェック
        user = CustomUser.objects.get(id=request.user.id)
        # userがサイト管理者または店舗管理者かチェック
        if user.is_superuser or user.is_admin:
            # 対象の店舗を取得
            managed_restaurant = Restaurant.objects.get(id=restaurant_id)
            # 対象の店舗のレビューを取得
            managed_restaurant_reviews = Review.objects.filter(restaurant_id=restaurant_id)
            # レビューがあるかチェック
            if managed_restaurant_reviews:
                return render(request, 'managed_restaurant_review.html', context={
                    'managed_restaurant': managed_restaurant,
                    'managed_restaurant_reviews': managed_restaurant_reviews,
                })
            else:
                return render(request, 'managed_restaurant_review.html', context={
                    'managed_restaurant': managed_restaurant,
                    'message': 'レビューはありません。',
                })
        else:
            return render(request, 'access_denied.html', context={
                'message': 'このページは管理者専用です。',
                'url': reverse('admin_top'),
                'text': '管理者トップ',
            })
    else:
        raise Http404

### 管理店舗の予約一覧（サイト管理者、店舗管理者専用） ###
@login_required
def list_managed_restaurant_reserve(request, restaurant_id):
    if request.method == 'GET':
        # ユーザーを取得して、ユーザーがいるかチェック
        user = CustomUser.objects.get(id=request.user.id)
        # userが店舗管理者かチェック
        if user.is_superuser or user.is_admin:
            # 対象の店舗を取得
            managed_restaurant = Restaurant.objects.get(id=restaurant_id)
            # 対象の店舗のレビューを取得
            managed_restaurant_reservations = Reservation.objects.filter(restaurant_id=restaurant_id)
            # 予約があるかチェック
            if managed_restaurant_reservations:
                return render(request, 'managed_restaurant_reserve.html', context={
                    'managed_restaurant': managed_restaurant,
                    'managed_restaurant_reservations': managed_restaurant_reservations,
                })
            else:
                return render(request, 'managed_restaurant_reserve.html', context={
                    'managed_restaurant': managed_restaurant,
                    'message': '予約はありません。',
                })
        else:
            return render(request, 'access_denied.html', context={
                'message': 'このページは管理者専用です。',
                'url': reverse('admin_top'),
                'text': '管理者トップ',
            })
    else:
        raise Http404

### csvダウンロード（店舗管理者専用） ###
@login_required
def download_as_csv(request):
    if request.method == 'POST':
        user = CustomUser.objects.get(id=request.user.id)
        # リクエストの値によって処理を分岐
        target_data = request.POST["choice"]
        # サイト管理者かチェック
        if user.is_superuser:
            # 店舗情報
            if target_data == 'restaurant':
                # Restaurantテーブルをすべて取得
                response = HttpResponse(content_type='text/csv; charset=UTF-8')
                filename = urllib.parse.quote((f'{target_data}.csv').encode("utf8"))
                response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(filename)
                writer = csv.writer(response)
                for restaurant in Restaurant.objects.all():
                    writer.writerow([restaurant.id, restaurant.restaurant_name, restaurant.description, restaurant.postal_code, restaurant.address, restaurant.opening, restaurant.closing, restaurant.regular_holiday, restaurant.seat_number, restaurant.phone_number, restaurant.create_at])
                return response
            # レビュー情報
            elif target_data == 'review':
                response = HttpResponse(content_type='text/csv; charset=UTF-8')
                filename = urllib.parse.quote((f'{target_data}.csv').encode("utf8"))
                response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(filename)
                writer = csv.writer(response)
                # すべての店舗を取得
                restaurants = Restaurant.objects.all()
                if restaurants:
                    # クエリセットをリスト化
                    restaurant_record_list = list(restaurants.values())
                    review_list = []
                    for restaurant in restaurant_record_list:
                        # 管理している店舗のidがrestaurant_idと一致するレビューを取得
                        try:
                            reviews = Review.objects.filter(restaurant_id=restaurant['id'])
                            # クエリセットをリスト化
                            review_record_list = list(reviews.values())
                            for review in review_record_list:
                                # レビューしたユーザー名を取得
                                try:
                                    review_user = CustomUser.objects.get(id=review['user_id'])
                                    review['username'] = review_user.get_nickname()
                                    review['restaurant_name'] = restaurant['restaurant_name']
                                    review_list.append(review)
                                except CustomUser.DoesNotExist:
                                    user = None
                        except Review.DoesNotExist:
                            review = None
                    for review in review_list:
                        writer.writerow([review['id'], review['restaurant_name'], review['username'], review['score'], review['review_title'], review['review_comment'], review['create_at']])
                    return response
                else:
                    # 店舗が存在しなければ店舗一覧へ
                    return render(request, 'list_managed_restaurant', context={
                        'message': '店舗が存在しません。',
                    })
            # 予約情報
            elif target_data == 'reservation':
                response = HttpResponse(content_type='text/csv; charset=UTF-8')
                filename = urllib.parse.quote((f'{target_data}.csv').encode("utf8"))
                response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(filename)
                writer = csv.writer(response)
                # すべての店舗を取得
                restaurants = Restaurant.objects.all()
                if restaurants:
                    # クエリセットをリスト化
                    restaurant_record_list = list(restaurants.values())
                    reservation_list = []
                    #店舗のidがrestaurant_idと一致する予約を取得
                    for restaurant in restaurant_record_list:
                        try:
                            reservations = Reservation.objects.filter(restaurant_id=restaurant['id'])
                            # クエリセットをリスト化
                            reservation_record_list = list(reservations.values())
                            for reservation in reservation_record_list:
                                # 予約したユーザー名を取得
                                try:
                                    reserve_user = CustomUser.objects.get(id=reservation['user_id'])
                                    reservation['username'] = reserve_user.get_nickname()
                                    reservation['restaurant_name'] = restaurant['restaurant_name']
                                    reservation_list.append(reservation)
                                except CustomUser.DoesNotExist:
                                    user = None
                        except Reservation.DoesNotExist:
                            reservation = None
                    for reservation in reservation_list:
                        writer.writerow([reservation['id'], reservation['restaurant_name'], reservation['username'], reservation['reservation_date'], reservation['reservation_start'],  reservation['reservation_end'],  reservation['number_of_people']])
                    return response
                else:
                    # 店舗が存在しなければ店舗一覧へ
                    return render(request, 'list_managed_restaurant', context={
                        'message': '店舗が存在しません。',
                    })
            # カテゴリ情報
            elif target_data == 'category':
                # Categoryテーブルを全件検索
                response = HttpResponse(content_type='text/csv; charset=UTF-8')
                filename = urllib.parse.quote((f'{target_data}.csv').encode("utf8"))
                response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(filename)
                writer = csv.writer(response)
                for category in Category.objects.all():
                    writer.writerow([category.id, category.category_name, category.create_at])
                return response
            else:
                raise Http404
        # 店舗管理者ユーザーかチェック
        elif user.is_admin:
            # 店舗情報
            if target_data == 'restaurant':
                # Restaurantテーブルをrestaurant_adminが一致するもので検索
                response = HttpResponse(content_type='text/csv; charset=UTF-8')
                filename = urllib.parse.quote((f'{target_data}.csv').encode("utf8"))
                response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(filename)
                writer = csv.writer(response)
                for restaurant in Restaurant.objects.filter(restaurant_admin_id=request.user.id):
                    writer.writerow([restaurant.id, restaurant.restaurant_name, restaurant.description, restaurant.postal_code, restaurant.address, restaurant.opening, restaurant.closing, restaurant.regular_holiday, restaurant.seat_number, restaurant.phone_number, restaurant.create_at])
                return response
            # レビュー情報
            elif target_data == 'review':
                response = HttpResponse(content_type='text/csv; charset=UTF-8')
                filename = urllib.parse.quote((f'{target_data}.csv').encode("utf8"))
                response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(filename)
                writer = csv.writer(response)
                # 管理者になっている店舗を取得
                restaurants = Restaurant.objects.filter(restaurant_admin_id=request.user.id)
                if restaurants:
                    # クエリセットをリスト化
                    restaurant_record_list = list(restaurants.values())
                    review_list = []
                    for restaurant in restaurant_record_list:
                        # 管理している店舗のidがrestaurant_idと一致するレビューを取得
                        try:
                            reviews = Review.objects.filter(restaurant_id=restaurant['id'])
                            # クエリセットをリスト化
                            review_record_list = list(reviews.values())
                            for review in review_record_list:
                                # レビューしたユーザー名を取得
                                try:
                                    review_user = CustomUser.objects.get(id=review['user_id'])
                                    review['username'] = review_user.get_nickname()
                                    review['restaurant_name'] = restaurant['restaurant_name']
                                    review_list.append(review)
                                except CustomUser.DoesNotExist:
                                    user = None
                        except Review.DoesNotExist:
                            review = None
                    for review in review_list:
                        writer.writerow([review['id'], review['restaurant_name'], review['username'], review['score'], review['review_title'], review['review_comment'], review['create_at']])
                    return response
                else:
                    # 店舗が存在しなければ店舗一覧へ
                    return render(request, 'list_managed_restaurant', context={
                        'message': '店舗が存在しません。',
                    })
            # 予約情報
            elif target_data == 'reservation':
                response = HttpResponse(content_type='text/csv; charset=UTF-8')
                filename = urllib.parse.quote((f'{target_data}.csv').encode("utf8"))
                response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(filename)
                writer = csv.writer(response)
                # 管理者になっている店舗を取得
                restaurants = Restaurant.objects.filter(restaurant_admin_id=request.user.id)
                if restaurants:
                    # クエリセットをリスト化
                    restaurant_record_list = list(restaurants.values())
                    reservation_list = []
                    #店舗のidがrestaurant_idと一致する予約を取得
                    for restaurant in restaurant_record_list:
                        try:
                            reservations = Reservation.objects.filter(restaurant_id=restaurant['id'])
                            # クエリセットをリスト化
                            reservation_record_list = list(reservations.values())
                            for reservation in reservation_record_list:
                                # 予約したユーザー名を取得
                                try:
                                    reserve_user = CustomUser.objects.get(id=reservation['user_id'])
                                    reservation['username'] = reserve_user.get_nickname()
                                    reservation['restaurant_name'] = restaurant['restaurant_name']
                                    reservation_list.append(reservation)
                                except CustomUser.DoesNotExist:
                                    user = None
                        except Reservation.DoesNotExist:
                            reservation = None
                    for reservation in reservation_list:
                        writer.writerow([reservation['id'], reservation['restaurant_name'], reservation['username'], reservation['reservation_date'], reservation['reservation_start'],  reservation['reservation_end'],  reservation['number_of_people']])
                    return response
                else:
                    # 店舗が存在しなければ店舗一覧へ
                    return render(request, 'list_managed_restaurant', context={
                        'message': '店舗が存在しません。',
                    })
            # カテゴリ情報
            elif target_data == 'category':
                # Categoryテーブルを全件検索
                response = HttpResponse(content_type='text/csv; charset=UTF-8')
                filename = urllib.parse.quote((f'{target_data}.csv').encode("utf8"))
                response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(filename)
                writer = csv.writer(response)
                for category in Category.objects.all():
                    writer.writerow([category.id, category.category_name, category.create_at])
                return response
            else:
                raise Http404
        else:
            return render(request, 'access_denied.html', context={
                'message': 'このページは管理者専用です。',
                'url': reverse('admin_top'),
                'text': '管理者トップ',
            })
    return render(request, 'download.html', context={})

### アカウント情報csvダウンロード（サイト管理者専用） ###
@login_required
def download_accounts_info(request):
    if request.method == 'GET':
        user = CustomUser.objects.get(id=request.user.id)
        # サイト管理者かどうかチェック
        if user.is_superuser:
            response = HttpResponse(content_type='text/csv; charset=UTF-8')
            filename = urllib.parse.quote(('accounts.csv').encode("utf8"))
            response['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(filename)
            writer = csv.writer(response)
            for user in CustomUser.objects.all():
                writer.writerow([user.id, user.email, user.nickname, user.phone_number, user.last_login, user.date_joined, user.update_at, user.is_superuser, user.is_admin])
            return response
        else:
            # サイト管理者でない場合は、アクセス拒否画面へ
            return render(request, 'access_denied.html', context={
                'message': 'このページはサイト管理者専用です。',
                'url': reverse('admin_top'),
                'text': '管理者トップ',
            })
    else:
        raise Http404

### アカウント検索（サイト管理者専用） ###
@login_required
def account_search(request):
    if request.method == 'GET':
        user = CustomUser.objects.get(id=request.user.id)
        # サイト管理者かどうかチェック
        if user.is_superuser:
            accounts = CustomUser.objects.all()
            keyword = request.GET.get('keyword')

            # keywordが入力されていたら、emailかニックネームでフィルタ
            if keyword:
                accounts = accounts.filter(
                    (Q(email__icontains=keyword)|Q(nickname__icontains=keyword))
                    )
                return render(request, 'managed_account.html', context={
                    'accounts': accounts,
                })
            else:
                return render(request, 'managed_account.html',context={
                    'accounts': accounts,
                })
        else:
            # サイト管理者でない場合は、アクセス拒否画面へ
            return render(request, 'access_denied.html', context={
                'message': 'このページはサイト管理者専用です。',
                'url': reverse('admin_top'),
                'text': '管理者トップ',
            })
    else:
        raise Http404

### アカウント一覧表示（サイト管理者専用） ###
@login_required
def list_managed_account(request):
    if request.method == 'GET':
        user = CustomUser.objects.get(id=request.user.id)
        # サイト管理者かどうかチェック
        if user.is_superuser:
            accounts = CustomUser.objects.all()
            return render(request, 'managed_account.html', context={
                'accounts': accounts,
            })
        else:
            # サイト管理者でない場合は、アクセス拒否画面へ
            return render(request, 'access_denied.html', context={
                'message': 'このページはサイト管理者専用です。',
                'url': reverse('admin_top'),
                'text': '管理者トップ',
            })
    else:
        raise Http404

### サブスクリプション登録確認画面（ログインが必要） ###
@login_required
def confirm_subscribe(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    if request.method == 'GET':
        return render(request, 'confirm_subscribe.html', context={
            'categories': categories,
        })
    else:
        raise Http404

### サブスクリプション解約確認画面（ログインが必要） ###
@login_required
def confirm_cancel_subscribe(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    # 有料会員かどうかチェック
    if Subscriber.objects.filter(user_id=request.user.id):
        # subscription_idを取得
        subscriber = Subscriber.objects.get(user_id=request.user.id)
        subscription_id = subscriber.subscription_id
        return render(request, 'confirm_cancel_subscribe.html', context={
            'categories': categories,
            'subscription_id': subscription_id,
        })
    else:
        return render(request, 'cancel.html', context={
                'categories': categories,
                'message': '有料会員ではありません。',
                'url': reverse('mypage'),
                'text': 'マイページ',
            })

### ### Stripe関連の処理（開始） ### ###
### Create Checkout Session（サブスクリプション登録、ログインが必要） ###
@login_required
def create_checkout_session(request, pk):
    # base表示用カテゴリ
    categories = Category.objects.all()
    if request.method == "POST":
        user_id = request.user.id
        # 既に有料会員だったら
        if Subscriber.objects.filter(user_id=user_id):
            return render(request, 'pay_success.html', context={
                'message': '既に有料会員登録が完了しています。',
                'text': 'TOP',
                'url': reverse('top'),
                'categories': categories,
            })
        else:
            # 対象のサブスクリプション商品と価格を取得
            subscription_product = SubscriptionProduct.objects.get(id=pk)
            price = SubscriptionPrice.objects.get(subscription_product=subscription_product)

            # ドメイン
            # YOUR_DOMAIN = "http://127.0.0.1:8000"
            YOUR_DOMAIN = "https://nagoyameshi-v2-2b170df35302.herokuapp.com"

            # 決済用セッション
            checkout_session = stripe.checkout.Session.create(
                # 決済方法
                payment_method_types=['card'],
                # クライアントID
                client_reference_id = request.user.id,
                # 決済詳細
                line_items=[
                    {
                        'price': price.stripe_price_id,       # 価格IDを指定
                        'quantity': 1,                        # 数量
                    },
                ],
                # POSTリクエスト時にメタデータ取得
                metadata = {
                            "stripe_product_id":subscription_product.stripe_product_id,
                            },
                mode='subscription',                               # 決済手段（一括）
                success_url=YOUR_DOMAIN + '/pay_success/',        # 決済成功時のリダイレクト先
                cancel_url=YOUR_DOMAIN + '/pay_cancel/',          # 決済キャンセル時のリダイレクト先
            )
            return redirect(checkout_session.url)
    else:
        raise Http404

### Event Handler ###
@csrf_exempt
def stripe_webhook(request):
    # サーバーのイベントログからの出力ステートメント
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        # 有効でないpayload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # 有効でない署名
        return HttpResponse(status=400)
    
    # checkout.session.completedイベント検知
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # イベント情報取得
        user_id = session.get('client_reference_id')
        customer = CustomUser.objects.get(id=user_id)
        stripe_id = session.get('customer')
        subscription_id = session.get('subscription')
        stripe_product_id = session['metadata']['stripe_product_id'] # 購入商品情報
        product = SubscriptionProduct.objects.get(stripe_product_id=stripe_product_id)
        product_amount = session['amount_total'] # 購入金額（手数料抜き）

        # DBに結果を保存
        SaveTransaction(customer, product, product_amount)
        SaveSubscriber(customer, stripe_id, subscription_id)
    
    # サブスクリプション停止時のイベント検知
    elif event['type'] == 'customer.subscription.updated':
        session = event['data']['object']

        print(session)

        # イベント情報取得
        stripe_id = session.get('customer')

        # cancel_subscribe関数に情報を渡す
        cancel_subscribe(stripe_id)

    # Passed signature verification
    return HttpResponse(status=200)

### Transactionモデルへの保存 ###
def SaveTransaction(customer, product, product_amount):
    # DB保存
    saveData = Transaction.objects.get_or_create(
                        date = datetime.datetime.now(),
                        customer = customer,
                        product  = product,
                        product_amount = product_amount
                        )
    return saveData

### Subscriberモデルへの保存 ###
def SaveSubscriber(customer, stripe_id, subscription_id):
    # DB保存
    saveData = Subscriber.objects.get_or_create(
                        user = customer,
                        create_at  = datetime.datetime.now(),
                        update_at = datetime.datetime.now(),
                        stripe_id = stripe_id,
                        subscription_id = subscription_id
                        )
    return saveData

### 決済完了画面 ###
def paysuccess(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    return render(request,"pay_success.html", context={
        'message': '決済が完了しました!',
        'text': 'TOP',
        'url': reverse('top'),
        'categories': categories,
    })

### 決済キャンセル画面 ###
def paycancel(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    return render(request,"pay_cancel.html", context={
        'message': 'キャンセルしました。',
        'text': 'TOP',
        'url': reverse('top'),
        'categories': categories,
    })

### 有料会員登録の解約（サブスクリプション停止） ###
@csrf_exempt
@login_required
def cancel_subscription_session(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    if request.method == 'POST':
        # ユーザーIDを取得
        user_id = request.user.id
        # 有料会員かどうかチェック
        if Subscriber.objects.filter(user_id=user_id):
            customer = Subscriber.objects.get(user_id=user_id)
            subscription_id = request.POST.get('subscription_id')
            session = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True,
                metadata={
                    'customer_id': customer.stripe_id,
                    'meta_flag': 'cancel_scheduled',
                }
            )
            return render(request, 'success.html', context={
                'categories': categories,
                'message': '有料会員登録を解約しました。',
                'url': reverse('mypage'),
                'text': 'マイページ',
            })
        else:
            return render(request, 'cancel.html', context={
                'categories': categories,
                'message': '有料会員ではありません。',
                'url': reverse('mypage'),
                'text': 'マイページ',
            })
    else:
        raise Http404

### 有料会員登録の解約 ###
def cancel_subscribe(stripe_id):
    # base表示用カテゴリ
    categories = Category.objects.all()
    # DBから対象のデータを削除
    subscribe = Subscriber.objects.get(stripe_id=stripe_id)
    subscribe.delete()
    return HttpResponse(status=200)

### ### Stripe関連の処理（終了） ### ###

### 無料会員登録の解約 ###
@login_required
def cancel_account(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    user = CustomUser.objects.get(id=request.user.id)
    if request.method == 'POST':
        if 'btn_ok' in request.POST:
            try:
                user = CustomUser.objects.get(id=request.user.id)
                if user:
                    user.delete()
                    return render(request, 'success.html', context={
                        'categories': categories,
                        'message': '無料会員登録を解除しました',
                        'text': 'TOP',
                        'url': reverse('top'),
                    })
            except:
                # 会員でないのにアクセスした場合は404エラー
                raise Http404
        elif 'btn_cancel' in request.POST:
            return render(request, 'mypage.html', context={
                'categories': categories,
            })
    else:
        # 有料会員だったら有料会員の解約ページへ
        if Subscriber.objects.filter(user_id=request.user.id):
            return render(request, 'cancel_subscribe.html', context={
                'categories': categories,
                'message': 'あなたは有料会員です。'
            })
        # 無料会員なら無料会員の解約ページへ
        else:
            return render(request, 'cancel_account.html', context={
                'categories': categories,
            })

### 売上管理 ###
def uriage_view(request):
    # base表示用カテゴリ
    categories = Category.objects.all()
    try:
        year = int(request.GET.get("y"))
        # 最終日を取り出す
        month_list = []
        for m in range(12):
            month_list.append([m+1, calendar.monthrange(year, m+1)[1]])
        
        print(month_list)

        uriages = []
        for m in month_list:
            s_date = str(year) + "-" + str(m[0]) + "-1"
            e_date = str(year) + "-" + str(m[0]) + "-" + str(m[1])
    
            uriages.append(Subscriber.objects.filter(update_at__gte=s_date, update_at__lte=e_date).count())
        
        print(uriages)

        return render(request, 'uriage.html', context={
            'categories': categories,
            'uriages': uriages,
            'year': year,
        })
    except:
        return HttpResponse('不正な値です。')


        

