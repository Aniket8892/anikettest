from django.shortcuts import render,render_to_response,redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from yoolotto.rest.decorators import rest, Authenticate
from django.db.models import Sum,Count
from django.http import HttpResponse, HttpResponseNotFound,HttpResponseRedirect
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
import json
from datetime import datetime
import datetime
from yoolotto.dashboard_app.forms import EntriesForm,GoogleAnalyticsForm
from yoolotto.dashboard_app.models import Entries,GoogleAnalytics
import math
import csv
import glob
import MySQLdb
connection=MySQLdb.connect(host='127.0.0.1',port=3306,user='root',passwd='root',db='yoo_db_git')
# Create your views here.
class FillDetails(View):
	@rest
	def get(self,request):
		form = EntriesForm()
		return render(request,'dashboard/entries.html',{'form': form})
		
	
	def post(self,request):
		form = EntriesForm(request.POST)
		if form.is_valid():
			entry = form.save(commit=False)
			#print "impressions",type(form.cleaned_data['impressions'])
			#print "revenue",type(form.cleaned_data['revenue'])
			impressions=float(form.cleaned_data['impressions'])
			revenue=float(form.cleaned_data['revenue'])
			#import pdb;
			#pdb.set_trace()
			try:
				entry.ecpm = round(float(revenue*1000)/impressions,2)
				print "ok"
				print entry.ecpm
			except:
				entry.ecpm=0
				print "error"
			entry.save()
			return HttpResponseRedirect("/dashboard/")


####### Revenue on daily basis ##########
def day_wise_revenue(date):
	video_revenue_date_wise=Entries.objects.filter(provider_type='video',entry_date=date).aggregate(Sum('revenue'))['revenue__sum']
	banner_revenue_date_wise=Entries.objects.filter(provider_type='banner',entry_date=date).aggregate(Sum('revenue'))['revenue__sum']
	interstitial_revenue_date_wise=Entries.objects.filter(provider_type='interstitial',entry_date=date).aggregate(Sum('revenue'))['revenue__sum']

	return {"video_revenue":video_revenue_date_wise,"banner_revenue":banner_revenue_date_wise,"interstitial_revenue":interstitial_revenue_date_wise}


#### Total devices (ios and android) from GoogleAnalytics via form we have created
#### New devices via queries
### Old devices=total - new
def calculate_no_of_android_devices(date):
	cursor=connection.cursor()
	cursor1=connection.cursor()
	total_android="select nos_of_devices from google_analytics where device='ANDROID' and date(entry_date)='{0}';".format(date)
	new_android="select count(*) from user_coins_earn_history where source='new_user' and device_type='ANDROID' and date(added_at)='2016-12-06';"
	cursor.execute(total_android)
	cursor1.execute(new_android)
	try:
		new_android_devices=int(cursor1.fetchone()[0])
	except:
		new_android_devices=0
	try:
		total_android_devices=int(cursor.fetchone()[0])
	except:
		total_android_devices=0
	existing_android_devices=total_android_devices-new_android_devices
	
	return {"total_android_devices":total_android_devices,"new_android_devices":new_android_devices,"existing_android_devices":existing_android_devices}


def calculate_no_of_ios_devices(date):
	cursor=connection.cursor()
	cursor1=connection.cursor()
	total_ios="select nos_of_devices from google_analytics where device='IOS' and date(entry_date)='{0}';".format(date)
	new_ios="select count(*) from user_coins_earn_history where source='new_user' and device_type='IPHONE' and date(added_at)='2016-12-06';"
	cursor.execute(total_ios)
	cursor1.execute(new_ios)
	try:
		new_ios_devices=int(cursor1.fetchone()[0])
	except:
		new_ios_devices=0
	try:
		total_ios_devices=int(cursor.fetchone()[0])
	except:
		total_ios_devices=0
	existing_ios_devices=total_ios_devices-new_ios_devices
	
	return {"total_ios_devices":total_ios_devices,"new_ios_devices":new_ios_devices,"existing_ios_devices":existing_ios_devices}


#### Users who have earned yoobux and watched videos #####
def user_activity(date):
	cursor1=connection.cursor()
	cursor2=connection.cursor()
	cursor3=connection.cursor()
	cursor4=connection.cursor()
	cursor5=connection.cursor()
	cursor6=connection.cursor()
	total_usr="select sum(h.credit_coins) as total_coins from user_history h inner join user u on h.user_id=u.id where date(h.added_at)='{0}' group by h.user_id having total_coins >=0  order by sum(h.credit_coins) ;".format(date)
	usr_ernd_zero_yoobx="select sum(h.credit_coins) as total_coins from user_history h inner join user u on h.user_id=u.id where date(h.added_at)='{0}' group by h.user_id having total_coins =0  order by sum(h.credit_coins) ;".format(date)
	watched_videos="select count(distinct(user_id)) as total_users from user_history where source_id in (14) and date(added_at)='{0}';".format(date)
	user_earned_one_or_more_yoobux="select sum(h.credit_coins) as total_coins from user_history h inner join user u on h.user_id=u.id where date(h.added_at)='{0}' group by h.user_id having total_coins >= 1  order by sum(h.credit_coins) ;".format(date)
	ios_usr_in_hun_clb ="select sum(h.credit_coins) as total_coins from user_history h inner join user u on h.user_id=u.id where date(h.added_at)='{0}'and device_type='IPHONE' group by h.user_id having total_coins >=100 order by sum(h.credit_coins) ;".format(date)
	android_usr_in_hun_clb="select sum(h.credit_coins) as total_coins from user_history h inner join user u on h.user_id=u.id where date(h.added_at)='{0}'and device_type='ANDROID' group by h.user_id having total_coins >=100 order by sum(h.credit_coins) ;".format(date)

	total_user_count=int(cursor1.execute(total_usr))
	zero_yoobux_user=int(cursor2.execute(usr_ernd_zero_yoobx))
	user_earned_one_or_more_yoobux=int(cursor3.execute(user_earned_one_or_more_yoobux))
	user_who_did_activity=total_user_count-zero_yoobux_user
	cursor4.execute(watched_videos)
	try:
		usr_watched_videos=int(cursor4.fetchone()[0])
	except:
		usr_watched_videos=0
	
	ios_hundred_club=int(cursor5.execute(ios_usr_in_hun_clb))
	android_hundred_club=int(cursor6.execute(android_usr_in_hun_clb))

	no_of_android_device=calculate_no_of_android_devices(date)["total_android_devices"]
	no_of_ios_device=calculate_no_of_ios_devices(date)["total_ios_devices"]
	total_device=no_of_ios_device+no_of_android_device

	try:
		avg_of_device_per_user=round(total_device/float(user_earned_one_or_more_yoobux),1)
	except:
		avg_of_device_per_user=0
	try:
		avg_of_device_per_video_usr=round(float(total_device-(user_earned_one_or_more_yoobux-usr_watched_videos))/usr_watched_videos,1)
	except:
		avg_of_device_per_video_usr=0
	return {"total_user":total_user_count,"user_who_did_activity":user_who_did_activity,"usr_watched_videos":usr_watched_videos,"user_earned_one_or_more_yoobux":user_earned_one_or_more_yoobux,"ios_hundred_club":ios_hundred_club,"android_hundred_club":android_hundred_club,"avg_of_device_per_user":avg_of_device_per_user
	,"avg_of_device_per_video_usr":avg_of_device_per_video_usr,"no_of_android_device":no_of_android_device,"no_of_ios_device":no_of_ios_device}


def calculate_avg_ecpm(date):
	cursor1=connection.cursor()
	cursor2=connection.cursor()
	cursor3=connection.cursor()
	cursor4=connection.cursor()

	video_revenue_query="select sum(revenue) from dashboard_entries where provider_type IN ('video') and entry_date='{0}';".format(date)
	banner_revenue_query="select sum(revenue) from dashboard_entries where provider_type IN ('banner','interstitial') and entry_date='{0}';".format(date) 
	video_impression_query="select sum(impressions) from dashboard_entries where provider_type IN ('video') and entry_date='{0}';".format(date)
	banner_impression_query="select sum(impressions) from dashboard_entries where provider_type IN ('banner','interstitial') and entry_date='{0}';".format(date) 
	#sum_ecpm_video="select sum(ecpm) from dashboard_entries where provider_type IN ('video') and entry_date='{0}';".format(date) 
	#count_ecpm_video="select count(ecpm) from dashboard_entries where provider_type IN ('video') and entry_date='{0}';".format(date) 

	cursor1.execute(video_revenue_query)
	cursor2.execute(banner_revenue_query)
	cursor3.execute(video_impression_query)
	cursor4.execute(banner_impression_query)

	try:
		video_revenue=int(cursor1.fetchone()[0])
	except:
		video_revenue=0

	try:
		banner_revenue=int(cursor2.fetchone()[0])
	except:
		banner_revenue=0

	try:
		video_impression=int(cursor3.fetchone()[0])
	except:
		video_impression=0

	try:
		banner_impression=int(cursor4.fetchone()[0])
	except:
		banner_impression=0

	try:
		avg_ecpm_video=round((video_revenue*1000)/video_impression,2)
	except:
		avg_ecpm_video=0

	try:
		avg_ecpm_banint=round((banner_revenue*1000)/banner_impression,2)
	except:
		avg_ecpm_banint=0

	total_revenue=video_revenue+banner_revenue

	# sum_video=int(cursor1.execute(sum_ecpm_video))
	# count_video=int(cursor2.execute(count_ecpm_video))

	# try:
	# 	avg_ecpm_video=round(sum_video/count_video,2)
	# except:
	# 	avg_ecpm_video=0


	# sum_ecpm_banint="select sum(ecpm) from dashboard_entries where provider_type IN ('banner','interstitial') and entry_date='{0}';".format(date) 
	# count_ecpm_banint="select count(ecpm) from dashboard_entries where provider_type IN ('banner','interstitial') and entry_date='{0}';".format(date) 

	# sum_banint=int(cursor1.execute(sum_ecpm_banint))
	# count_banint=int(cursor2.execute(count_ecpm_banint))

	# try:
	# 	avg_ecpm_banint=round(sum_banint/count_banint,2)
	# except:
	# 	avg_ecpm_banint=0

	return {"avg_ecpm_video":avg_ecpm_video,"avg_ecpm_banint":avg_ecpm_banint,"video_revenue":video_revenue,"banner_revenue":banner_revenue,"total_revenue":total_revenue}

class DailyReport(View):
	def get(self,request):
		date=request.GET.get('date','')

		#print sum_ecpm,count_ecpm
		try:
			avg_ecpm=round(sum_ecpm/count_ecpm,2)
		except:
			avg_ecpm=0

		rev=day_wise_revenue(date)
		android_info=calculate_no_of_android_devices(date)
		ios_info=calculate_no_of_ios_devices(date)
		usr_activity=user_activity(date)

		f = open('DailyReport-{0}.csv'.format(date),'wb')
		try:
		    writer = csv.writer(f)
		    writer.writerow( ('Date','Video revenue', 'Banner revenue', 'Interstitial revenue','Avg ecpm') )
		    writer.writerow( (date,rev["video_revenue"], rev["banner_revenue"], rev["interstitial_revenue"], avg_ecpm) )
		finally:
		    f.close()
		return HttpResponse("Ok")
		
class MonthlyReport(View):
	def post(self,request):
		interesting_files = glob.glob("*.csv") 
		f = open('output.csv','wb')
		writer = csv.writer(f)
		writer.writerow(("Date","Video revenue","Banner revenue","Interstitial revenue"))
		for filename in interesting_files:
			f = open(filename, 'rb')
			header = next(f,"None")
			reader=csv.reader(f)
			for line in reader:
				writer.writerow(line)

		return HttpResponse("Ok")
		


class GoogleAnalyticsDetail(View):
	@rest
	def get(self,request):
		form = GoogleAnalyticsForm()
		return render(request,'dashboard/googleanalytics.html',{'form': form})

	def post(self,request):
		form = GoogleAnalyticsForm(request.POST)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect("/dashboard/googleform/")



