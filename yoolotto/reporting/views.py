from django.shortcuts import render,render_to_response
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from yoolotto.rest.decorators import rest, Authenticate
import matplotlib.pyplot as plt
from django_pandas.io import read_frame
from django.db.models import Sum,Count
from yoolotto.second_chance.models import AppromoterPostbackDetails,UserCoinsSpendHistory,UserDeviceEarnHistory
from yoolotto.user.models import *
from yoolotto.second_chance.models import *
from django.http import HttpResponse, HttpResponseNotFound,HttpResponseRedirect
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
import json
from datetime import datetime
import datetime
from yoolotto.coin.models import *
import math
from django.contrib.auth import authenticate, login,logout
#from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
# Create your views here.

####Aniket Code starts here ########

def AESencrypt(password, plaintext, base64=False):
    import hashlib, os
    from Crypto.Cipher import AES
    SALT_LENGTH = 32
    DERIVATION_ROUNDS=1337
    BLOCK_SIZE = 16
    KEY_SIZE = 32
    MODE = AES.MODE_CBC
    
    salt = os.urandom(SALT_LENGTH)
    iv = os.urandom(BLOCK_SIZE)
    
    paddingLength = 16 - (len(plaintext) % 16)
    paddedPlaintext = plaintext+chr(paddingLength)*paddingLength
    derivedKey = password
    for i in range(0,DERIVATION_ROUNDS):
        derivedKey = hashlib.sha256(derivedKey+salt).digest()
    derivedKey = derivedKey[:KEY_SIZE]
    cipherSpec = AES.new(derivedKey, MODE, iv)
    ciphertext = cipherSpec.encrypt(paddedPlaintext)
    ciphertext = ciphertext + iv + salt
    if base64:
        import base64
        return base64.b64encode(ciphertext)
    else:
        return ciphertext.encode("hex")

def AESdecrypt(password, ciphertext, base64=False):
    import hashlib
    from Crypto.Cipher import AES
    SALT_LENGTH = 32
    DERIVATION_ROUNDS=1337
    BLOCK_SIZE = 16
    KEY_SIZE = 32
    MODE = AES.MODE_CBC
    
    if base64:
        import base64
        decodedCiphertext = base64.b64decode(ciphertext)
    else:
        decodedCiphertext = ciphertext.decode("hex")
    startIv = len(decodedCiphertext)-BLOCK_SIZE-SALT_LENGTH
    startSalt = len(decodedCiphertext)-SALT_LENGTH
    data, iv, salt = decodedCiphertext[:startIv], decodedCiphertext[startIv:startSalt], decodedCiphertext[startSalt:]
    derivedKey = password
    for i in range(0, DERIVATION_ROUNDS):
        derivedKey = hashlib.sha256(derivedKey+salt).digest()
    derivedKey = derivedKey[:KEY_SIZE]
    cipherSpec = AES.new(derivedKey, MODE, iv)
    plaintextWithPadding = cipherSpec.decrypt(data)
    paddingLength = ord(plaintextWithPadding[-1])
    plaintext = plaintextWithPadding[:-paddingLength]
    return plaintext




def yoobux_calculation(video_params,bannerad_params,total_video_count,total_banner_ad_count):
    '''
        All that param and count must in int datatype to get very accurate result.

    '''
    bannerad_bal = total_banner_ad_count % bannerad_params
    print "b",bannerad_bal
    video_bal =  total_video_count % video_params
    print "v",video_bal
    #interstital_bal = total_interstial_count % interstial_param
    #print "i",interstital_bal
    yoobux = 0
    yoobux=(total_video_count / video_params) + (total_banner_ad_count / bannerad_params)
    #remaining_equivalent_video_count = video_bal + bannerad_bal / video_params + interstital_bal / video_params
    remaining_equivalent_video_count = video_bal + bannerad_bal / (bannerad_params/video_params) 
    if remaining_equivalent_video_count >= video_params:
        yoobux += remaining_equivalent_video_count / video_params
        video_bal =  remaining_equivalent_video_count % video_params
        #bannerad_bal = bannerad_bal % video_params
        bannerad_bal = bannerad_bal % (bannerad_params/video_params)
    #interstital_bal = interstital_bal % video_params
        #interstital_bal = interstital_bal % (interstial_param/video_params)
    return {"yoo_bux":float(yoobux)/100,"video_bal":video_bal,"bannerad_bal":bannerad_bal,"coins":yoobux}




class Home(View):
    @rest
    @method_decorator(csrf_protect)
    def get(self,request):
        return render(request,'reporting/homepage.html')


    #@rest
    #@method_decorator(csrf_protect)
    def post(self,request):
        username=request.POST.get("uname","")
        password=request.POST.get("psw","")
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect("suspect/")
        else:
            return HttpResponseRedirect("/reporting/")




class Logout(View):
    @method_decorator(csrf_protect)
    @method_decorator(login_required(login_url='/reporting/'))
    def get(self,request):
        print "In"
        logout(request)
        print "Logged out"
        return HttpResponseRedirect('/reporting/')


class SuspectedUsers(View):
    @method_decorator(csrf_protect)
    @method_decorator(login_required(login_url='/reporting/'))
    def get(self,request):
        
        #print request.GET
        suspects=[]

        suspected_user=SuspectedUser.objects.all()
        for suspect in suspected_user:
            suspect_details={}
            try:
                suspect_details["email"]=suspect.user_email()
                suspect_details["device_id"]=suspect.device_id()
                suspect_details["reason"]=suspect.reason
                suspect_details["email_key"]= AESencrypt("password",suspect_details["email"])
                suspect_details["device_key"] = AESencrypt("password",suspect_details["device_id"])
            
            except:
                pass
            suspects.append(suspect_details)

        page = request.GET.get('page', 1)

        paginator = Paginator(suspects,5)
        try:
            users = paginator.page(page)
        except PageNotAnInteger:
            users = paginator.page(1)
        except EmptyPage:
            users = paginator.page(paginator.num_pages)

        return render(request, 'reporting/suspicious_user_list_new.html', { 'users': users,'admin':request.user.email})


    @method_decorator(csrf_protect)
    @method_decorator(login_required(login_url='/reporting/'))
    def post(self,request):
        suspects=[]
        email=request.POST.get('email_id','')
        #print email
        #status=request.POST.get('status','')
        start_date=request.POST.get('start_date','')
        #print request.POST.get('end_date','')
        end_date=request.POST.get('end_date','')

        #search_param=request.META['HTTP_YOO_EMAIL_ID']     ####Via postmaster header #####
        #search_param=json.loads(request.body)["email_id"]   ####Via postmaster body #####

        if email!='' and start_date !='' and end_date!='':
            suspected_user=SuspectedUser.objects.filter(user_device__user__email=email,created_date__range=(start_date,end_date)).values("user_device__user__email","user_device__device_id","reason")
        
        elif email=='' and start_date !='' and end_date!='':
            suspected_user=SuspectedUser.objects.filter(created_date__range=(start_date,end_date)).values("user_device__user__email","user_device__device_id","reason")

        elif email!='' and start_date =='' and end_date=='':
            suspected_user=SuspectedUser.objects.filter(user_device__user__email=email).values("user_device__user__email","user_device__device_id","reason")

        else:
            suspected_user=SuspectedUser.objects.all().values("user_device__user__email","user_device__device_id","reason")

        #suspected_user=SuspectedUser.objects.filter(user_device__user__email=email,created_date__range=(start_date,end_date)).values("user_device__user__email","user_device__device_id","reason")
        for suspect in suspected_user:
            suspect_details={}
            suspect_details["email"]=suspect["user_device__user__email"]
            suspect_details["device_id"]=suspect["user_device__device_id"]
            suspect_details["reason"]=suspect["reason"]
            suspect_details["email_key"]= AESencrypt("password",suspect_details["email"])
            suspect_details["device_key"]= AESencrypt("password",suspect_details["device_id"])
            suspects.append(suspect_details)

        page = request.GET.get('page', 1)

        paginators = Paginator(suspects,10)
        try:
            postusers = paginators.page(page)
        except PageNotAnInteger:
            postusers = paginators.page(1)
        except EmptyPage:
            postusers = paginators.page(paginators.num_pages)

        return render(request, 'reporting/suspicious_user_list_new.html', { 'users': postusers ,'admin':request.user.email})


class SuspectedEmailDetails(View):
    @method_decorator(csrf_protect)
    @method_decorator(login_required(login_url='/reporting/'))
    def get(self,request,code):
        suspects=[]
        email=AESdecrypt("password",code)
        suspected_user=SuspectedUser.objects.filter(user_device__user__email=email).values("user_device__user__id","user_device__user__email","user_device__device_id","reason","impression_ref__total_banner_count","impression_ref__total_video_count","impression_ref__list_of_providers","created_date","user_device__last_unblocked_date","user_device__user__added_at")
        user_email=email
        coin=EmailCoins.objects.filter(email=email).values_list("coins",flat=True)[0]
        amount=EmailCoins.objects.filter(email=email).values_list("dollar_amount",flat=True)[0]
        added_at=YooLottoUser.objects.filter(email=email).values_list("added_at",flat=True)[0]

        for suspect in suspected_user:
            suspect_details={}
            suspect_details["user_id"]=suspect["user_device__user__id"]
            suspect_details["device_id"]=suspect["user_device__device_id"]
            suspect_details["app_version"]=UserDeviceDetails.objects.filter(device_id=suspect_details["device_id"]).values_list("app_version",flat=True)[0]
            suspect_details["device_type"]=UserDeviceDetails.objects.filter(device_id=suspect_details["device_id"]).values_list("device_type",flat=True)[0]
            suspect_details["coins_per_device"]=UserDeviceEarnHistory.objects.filter(user_device__device_id=suspect_details["device_id"]).aggregate(sum=Sum("credit_coins"))["sum"]
            suspects.append(suspect_details)

        page = request.GET.get('page', 1)

        paginator = Paginator(suspects,5)
        try:
            users = paginator.page(page)
        except PageNotAnInteger:
            users = paginator.page(1)
        except EmptyPage:
            users = paginator.page(paginator.num_pages)

        return render(request, 'reporting/suspicious_user_detail_new.html', { 'users': users,'user_email':user_email,'coin':coin,'amount':amount,'added_at':added_at,'admin':request.user.email})


    @method_decorator(csrf_protect)
    @method_decorator(login_required(login_url='/reporting/'))
    def post(self,request,code):
        email=AESdecrypt("password",code)
        status=request.POST.get("action","")
        comment=request.POST.get("comment","")
        suspect=YooLottoUser.objects.get(email=email)
        comment=AdminComment(admin=request.user,comment=comment,suspect=suspect,status=status)
        comment.save()
        return HttpResponseRedirect('/reporting/suspect/suspect_details_email/%s'%code)
        


class SuspectedDeviceDetails(View):
    @method_decorator(csrf_protect)
    @method_decorator(login_required(login_url='/reporting/'))
    def get(self,request,code):
        suspects=[]
        info_per_email=[]

        device_id=AESdecrypt("password",code)
        suspect_details={}
        device_details=UserDeviceDetails.objects.get(device_id=device_id)
        suspect_details["app_version"]=device_details.app_version
        suspect_details["device_type"]=device_details.device_type
        suspect_details["device_token"]=device_details.device_token
        suspect_details["email"]=device_details.user.email
        suspect_details["added_at"]=device_details.added_at
        suspect_details["credit_amount"]=UserDeviceEarnHistory.objects.filter(user_device__device_id=device_id).aggregate(sum=Sum("credit_amount"))["sum"]
        suspect_details["total_video_impression"]=SuspectedUser.objects.filter(user_device__device_id=device_id).aggregate(total_video_count=Sum("impression_ref__total_video_count"))["total_video_count"]
        suspect_details["total_banner_impression"]=SuspectedUser.objects.filter(user_device__device_id=device_id).aggregate(total_banner_count=Sum("impression_ref__total_banner_count"))["total_banner_count"]
        suspect_details["earning_with_pacing"]=yoobux_calculation(18,180,suspect_details["total_video_impression"],suspect_details["total_banner_impression"])["yoo_bux"]
        #print suspect_details
        source_obj=CoinSource.objects.get(source_name='dwolla_cash')
        suspect_details["total_cashout"]=UserCoinsHistory.objects.filter(user__email=suspect_details["email"],source=source_obj).aggregate(Sum("debit_amount"))["debit_amount__sum"]

        emails_on_device=UserDeviceStatus.objects.filter(device_id=device_id).values("user__email")
        for email in emails_on_device:
            temp={}
            print email["user__email"]
            temp["login_id"]=YooLottoUser.objects.get(email=email["user__email"]).id
            temp["total_video_count"]=SuspectedUser.objects.filter(user_device__user__email=email["user__email"]).aggregate(total_video_count=Sum("impression_ref__total_video_count"))["total_video_count"]
            temp["total_banner_count"]=SuspectedUser.objects.filter(user_device__user__email=email["user__email"]).aggregate(total_banner_count=Sum("impression_ref__total_banner_count"))["total_banner_count"]
            temp["earning_with_pacing"]=yoobux_calculation(18,180,temp["total_video_count"],temp["total_banner_count"])["coins"]
            info_per_email.append(temp)
        
        return render(request,'reporting/user_device_detail_new.html', {'suspect':suspect_details,'details':info_per_email,'admin':request.user.email})

class BlockUser(View):
    @method_decorator(csrf_protect)
    @method_decorator(login_required(login_url='/reporting/'))
    def post(self,request):
        key=request.POST.get("key","")
        email=AESdecrypt("password",key)
        ###Blocking a user based on email ####
        YooLottoUser.objects.filter(email=email).update(is_blocked=True)
        return HttpResponseRedirect('/reporting/suspect')


# class TestHtml(View):
#     def get(self,request):
#         print "Ok"
#         return render(request,"reporting/user_device_detail.html")


#class SuspectedUsersFilter(View):
#     def get(self,request):
#         suspects=[]
        
#         #print request.GET.get("email_id","")
#         #print request.GET.get("start_date","")
#         #print request.GET.get("end_date","")
#         email=request.GET.get('email','')
#         print email
#         #status=request.POST.get('status','')
#         start_date=request.GET.get('start_date','')
#         print start_date
#         #print request.POST.get('end_date','')
#         end_date=request.GET.get('end_date','')
#         print end_date

#         #search_param=request.META['HTTP_YOO_EMAIL_ID']     ####Via postmaster header #####
#         #search_param=json.loads(request.body)["email_id"]   ####Via postmaster body #####

#         if email!='' and start_date !='' and end_date!='':
#             suspected_user=SuspectedUser.objects.filter(user_device__user__email=email,created_date__range=(start_date,end_date)).values("user_device__user__email","user_device__device_id","reason")
        
#         elif email=='' and start_date !='' and end_date!='':
#             suspected_user=SuspectedUser.objects.filter(created_date__range=(start_date,end_date)).values("user_device__user__email","user_device__device_id","reason")

#         elif email!='' and start_date =='' and end_date=='':
#             suspected_user=SuspectedUser.objects.filter(user_device__user__email=email).values("user_device__user__email","user_device__device_id","reason")

#         else:
#             suspected_user=SuspectedUser.objects.all().values("user_device__user__email","user_device__device_id","reason")

#         #suspected_user=SuspectedUser.objects.filter(user_device__user__email=email,created_date__range=(start_date,end_date)).values("user_device__user__email","user_device__device_id","reason")
#         for suspect in suspected_user:
#             suspect_details={}
#             suspect_details["email"]=suspect["user_device__user__email"]
#             suspect_details["device_id"]=suspect["user_device__device_id"]
#             suspect_details["reason"]=suspect["reason"]
#             suspect_details["email_key"]= AESencrypt("password",suspect_details["email"])
#             suspect_details["device_key"]= AESencrypt("password",suspect_details["device_id"])
#             suspects.append(suspect_details)

#         paginator = Paginator(suspects, 5) # Show 25 contacts per page
#         page = request.GET.get('page','1')
#         postusers = paginator.page(page)

#         return render(request, 'reporting/suspicious_user_list_new.html', { 'users': postusers ,'admin':request.user.email,'email':email,'start_date':start_date,'end_date':end_date})
