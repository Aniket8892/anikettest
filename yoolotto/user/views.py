import csv
import json
from yoolotto.user.yoo_functions import *
#import pudb; pu.db
from django.contrib.auth import hashers
from django.db import IntegrityError
from django.db.models import Count, Sum
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseNotFound
from django.views.generic import View
from yoolotto.second_chance.models import *
from yoolotto.rest import exceptions
from yoolotto.rest.decorators import rest, Authenticate
from yoolotto.coin.models import CoinTransaction, CoinTicketGenericTransaction, EmailCoins, DeviceCoins
from yoolotto.user.models import UserDeviceDetails as DeviceModel, YooLottoUser, UserPreference, UserToken, UserDetails, UserClientLogin, PasswordReset, UserCoinsDetails,FbDetails
from yoolotto.user.forms import UserUpdateForm, PreferenceUpdateForm
from yoolotto.lottery.models import LotteryTicketClient
from strgen import StringGenerator as SG
from django.db.models import F
import random
import datetime
from yoolotto.user.cipher import *
import hashlib
from django.template import Context
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
from django.contrib.staticfiles.templatetags.staticfiles import static
from yoolotto.user.models import *
from email.MIMEImage import MIMEImage
from yoolotto import settings
from yoolotto.coupon.models import CouponVendor as CouponVendorModel
from yoolotto.second_chance.models import FiberCoins,DeviceLoginDetails
from yoolotto.util.utilfunctions import get_decrypted_data,get_or_create_country_object

def AESencrypt(yoolotto, plaintext, base64=False):
    import hashlib, os
    from Crypto.Cipher import AES
    SALT_LENGTH = 17
    DERIVATION_ROUNDS=1337
    BLOCK_SIZE = 16
    KEY_SIZE = 32
    MODE = AES.MODE_CBC
     
    salt = os.urandom(SALT_LENGTH)
    iv = os.urandom(BLOCK_SIZE)
     
    paddingLength = 16 - (len(plaintext) % 16)
    paddedPlaintext = plaintext+chr(paddingLength)*paddingLength
    derivedKey = yoolotto
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


# class to register user
class RegisterUser(View):
    @rest
    #@Authenticate()
    def post(self,request):
        device_type = request.META['HTTP_YOO_DEVICE_TYPE']
        app_version = request.META["HTTP_YOO_APP_VERSION"]
        user_country = request.META.get("HTTP_YOO_COUNTRY_NAME","USA")
        country_code = request.META.get("HTTP_YOO_COUNTRY_CODE","US")
        #print "device_type",device_type
        #print "app_version",app_version
        #print "country",user_country
        #print "code",country_code
        user_data=get_decrypted_data(device_type,app_version,request.body)
        #print "data",user_data
        try:
            emaill = user_data['email']
            country_obj = get_or_create_country_object(country_code,user_country)
            user = YooLottoUser(name=user_data['user_name'],email=user_data['email'],password=hashers.make_password(user_data['password']),country=country_obj,add_initial_coins =1,not_referred=0)
            user.save()
            encrpted_id = AESencrypt("yoolotto", emaill)
            url = "https://test.yoolotto.com/verify_email?id=%s"%encrpted_id
            message_data = render_to_string('user/emailer.html', {'url' : url})

            # Sending mail to user for verification
            msg = EmailMultiAlternatives('Email Verification', message_data, 'postmaster@yoolotto.com',[user_data['email']])
            msg.attach_alternative(message_data, "text/html")
            msg.mixed_subtype = "related"  # Main content is now text/html
            image_path = settings.SITE_CONTAINER + settings.STATIC_URL + '/images/Picture1.png'
            fp = open(image_path, 'rb')
            msg_img = MIMEImage(fp.read())
            fp.close()
            msg_img.add_header('Content-ID', '<{}>'.format('Picture1.png'))
            msg.attach(msg_img)
            msg.send()
           
            user_details = UserDetails(user=user,phone=user_data['phone'],address=user_data['address'])
            user_details.save()
            
            return {"email":user.email,"user_name":user.name,"phone":user_details.phone,"id":user.id}
        except IntegrityError:
            raise exceptions.WebServiceException("Email already exist.")

class YooLoginaaaa(View):
    @rest
    def post(self, request):
        #print "META",request.META
        device_type = request.META['HTTP_YOO_DEVICE_TYPE']
        app_version = request.META["HTTP_YOO_APP_VERSION"]
        #print "device_type",device_type
        #print "app_version",app_version
        data=get_decrypted_data(device_type,app_version,request.body)
        #data=json.loads(request.body)
        #print "data",data
	device_id = request.META["HTTP_YOO_DEVICE_ID"]
        email = data['email']
        password = data['password']
        email_source = data['email_source']
	source ="intro_coins"
        user = None
        active_features= {}
        user_country = request.META.get("HTTP_YOO_COUNTRY_NAME","USA")
        country_code = request.META.get("HTTP_YOO_COUNTRY_CODE","US")
        print user_country,country_code
        #if device_type == "ANDROID" and app_version =="8.9": 
        try:
            country_obj = Country.objects.get(name__iexact=user_country)
            print "country_obj",country_obj   
            #obj_list=[]
            for obj in FeaturesList.objects.filter(country_id = country_obj):
                #print "True"
                #print obj.representation()
                #active_features.append(obj.representation())
                #print obj.name,obj.is_active
                active_features[obj.name]=obj.is_active
                # active_features["key"]=obj.name
                # active_features["value"]=obj.is_active
                #active_features=map(lambda x: x.representation(),obj)
                

        except Exception as e:
            raise exceptions.WebServiceException("This country does not have access of yoolotto.")
        print "feature1",active_features

        try:
            if email_source == "app":
                print "source "
                user = YooLottoUser.objects.get(email=data['email'])
                print user.id
        except:
            raise exceptions.WebServiceException("This email Id is not registered with the Yoolotto")
        if email_source =="app" and user.email_verified != 1:
            raise exceptions.WebServiceException("This email Id is not verified with the Yoolotto")
	coin_source = CoinSource.objects.get(source_name = source)
        if email_source == "twitter" or email_source == "facebook":
            try:
                user = YooLottoUser.objects.get(email=email)
            except:
                user = YooLottoUser(email = email)
                user.add_initial_coins=1
                user.country=country_obj
		user.not_referred=0
                user.save()
	try:
	    device_details = UserDeviceDetails.objects.get(device_id = device_id)
        #print "1"
	except:
	    device_details,created = UserDeviceDetails.objects.get_or_create(user=user,device_id = device_id)
        #print "2"
	if user.not_referred == 0 and device_details.not_referred == 0:
            showReferral = True
        else:
            showReferral = False
    	if email_source == "app":
            if hashers.check_password(password, user.password):
                email_coins,created = EmailCoins.objects.get_or_create(email = data['email'],defaults={"coins":10})
                if created:
                    email_coins.dollar_amount =0.1
                    email_coins.save()
		    user.referral = SG("[\u\d]{6}").render()
		    user.save()
		    Users_history = UserCoinsHistory(user = user,credit_coins = 10 ,source = coin_source,credit_amount = 0.1,device_type = device_type,net_amount = email_coins.dollar_amount,net_coins = email_coins.coins,app_version =app_version)
		    Users_history.save()
                    request.yoo["user"] = user
                print "feature2",active_features
                return {"total_coins": email_coins.coins,"success":True,"showReferral":showReferral,'features_list':active_features}
    	    else:
    		    raise exceptions.WebServiceException("Invalid Password")
    	else:
    	    if email_source == "twitter":
                email_coins,created = EmailCoins.objects.get_or_create(email = data['email'],defaults={"coins":10})
                if created:
                    email_coins.dollar_amount =0.1
                    email_coins.save()
		    user.referral = SG("[\u\d]{6}").render()
		    user.save()
		    Users_history = UserCoinsHistory(user = user,credit_coins = 10 ,source = coin_source,credit_amount = 0.1,device_type = device_type,net_amount = email_coins.dollar_amount,net_coins = email_coins.coins,app_version =app_version)
		    Users_history.save()
            elif email_source == "facebook":
                try:
                    fb_info = FbDetails.objects.get(fb_id = data['email'],fb_email = data['fb_email'])
                except:
                    try:
                        fb_info = FbDetails(fb_id = data['email'],fb_email = data['fb_email'])
                        fb_info.save()
                    except:
                        pass
		try:
		    previous_email_info = EmailCoins.objects.get(email=data['fb_email'])
		    previous_email_info.email = data['email']
		    previous_email_info.save()
		except:
		    pass
		email_coins,created = EmailCoins.objects.get_or_create(email = data['email'],defaults={"coins":10})
		if created:
		    email_coins.dollar_amount=0.1
		    email_coins.save()
		    user.referral = SG("[\u\d]{6}").render()
		    user.save()
		    Users_history = UserCoinsHistory(user = user,credit_coins = 10 ,source = coin_source,credit_amount = 0.1,device_type = device_type,net_amount = email_coins.dollar_amount,net_coins = email_coins.coins,app_version =app_version)
                    Users_history.save()

        
        return {"success": True,"total_coins": email_coins.coins,"showReferral":showReferral,'features_list':active_features}

class YooLogout(View):
    @rest
    @Authenticate()
    def post(self, request):
        try:
            user_client_login = UserClientLogin.objects.filter(device = request.yoo['device'],client_login = request.META['HTTP_YOO_EMAIL_ID'])[0]
            user_client_login.client_login = None
            user_client_login.save()
        except:
            pass
        device = request.yoo['device']
        print "deviceeeeeeeeeeeeeeee",device.id
        user = request.yoo['user']
        print "userrr",user.id
        device_user = DeviceModel.objects.get(id = int(device.id) ,user_id = int(user.id))
        device_user.device_token = None
        device_user.save()
        return {"success":True}

#class to logout user in app
class LogoutUser(View):
    @rest
    @Authenticate()
    def post(self, request):
        logout_user = UserClientLogin.objects.filter(device=request.yoo['device'])
        for user in logout_user:
            user.client_login = None
	        #user.email_source = None
            user.save()
    	try:
    	    device_record, created = DeviceCoins.objects.get_or_create(device_id=request.yoo['device'])
    	except:
    	    device_record = DeviceCoins.objects.filter(device_id = request.yoo['device'])[0]
	
        return {"coins":device_record.get_coins()}

#class to logout user in app
class Services(View):
    @rest
    @Authenticate()
    def get(self, request):
        yoo_prize_code =  random.randint(0,1)
        yoo_game_code =  random.randint(0,1)
        return {"yoo_prize":yoo_prize_code,"yoo_game":yoo_game_code}

# class to send mail to reset password, when user forgot password    
class ForgotPassword(View):
    @rest
    #@Authenticate()
    def post(self, request):
        
        from django.core.mail import EmailMessage
        
        device_type = request.META['HTTP_YOO_DEVICE_TYPE']
        app_version = request.META["HTTP_YOO_APP_VERSION"]
        data=get_decrypted_data(device_type,app_version,request.body)
        email = data["email"]
        try:
            YooLottoUser.objects.get(email=email)
            reset_code =  random.randint(1,100000000)
            PasswordResetRecord = PasswordReset.objects.filter(email=email)
            if PasswordResetRecord:
                PasswordResetRecord.update(code=reset_code, reset = False)
            else:
                PasswordReset(email=email, code=reset_code, reset = False).save()
            
            email = EmailMessage(' Reset Password Code YooLotto', 'reset_code = '+str(reset_code)+'', to=[email])
            email.send()
            
            return {"email":1}
        except:
            return {"email":0, "message": "email is not registered."}
        
class VerifyPasswordCode(View):
    @rest
    #@Authenticate()
    def post(self, request):
        data = json.loads(request.body)
        email = data["email"]
        code = data["code"]
        
        try:
            PasswordResetRecord = PasswordReset.objects.get(email=email,code=code)
            return {"verified":True}
        except:
            return {"verified":False}
        
class ResetPassword(View):
    @rest
   # @Authenticate()
    def post(self, request):
        try:
            device_type = request.META['HTTP_YOO_DEVICE_TYPE']
            app_version = request.META["HTTP_YOO_APP_VERSION"]
            data=get_decrypted_data(device_type,app_version,request.body)
            email = data["email"]
            password = data["password"]
            code = data["code"]
            try:
                PasswordResetRecord = PasswordReset.objects.get(email=email,code=code)
                YooLottoUser.objects.filter(email=email).update(password=hashers.make_password(password))
                return {"reset": True}
            except:
                raise exceptions.WebServiceException("Please enter valid verification code")
        except:
            return {"reset": False}
        


class Home(View):        
    @rest
    @Authenticate()
    def post(self, request):
        user = request.yoo["user"]
        device_type = request.META['HTTP_YOO_DEVICE_TYPE']
        app_version = request.META["HTTP_YOO_APP_VERSION"]
        data=get_decrypted_data(device_type,app_version,request.body)
	source="app_update_coins"
        device = request.yoo['device']
        device.device_token = data['pushToken']
	try:
	    if device.advertiser_id == data['advertiser_id']:
		pass
	    else:
		device.advertiser_id = data['advertiser_id']
	except:
	    pass
        device.save()
        print "userrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",user.id
        header_email = request.META['HTTP_YOO_EMAIL_ID']
        print "wjsaaaaaaaaa",header_email
        user1 = YooLottoUser.objects.get(email = header_email)
        #device_user,created= DeviceModel.objects.get_or_create(id = request.META["HTTP_YOO_DEVICE_ID"] ,user_id = int(user.id))
        email = data['email']
        if user1.add_initial_coins==0 and app_version>="7.0":
            try:
               email_coins = EmailCoins.objects.get(email = data['email'])
               email_coins.coins=10
               email_coins.dollar_amount=0.1
               user1.add_initial_coins=1
               email_coins.save()
               user1.save()
               coin_source = CoinSource.objects.get(source_name = source)
               user_history = UserCoinsHistory(user = user1,credit_coins = 10,source = coin_source,credit_amount = 0.1,device_type = device_type,net_amount = email_coins.dollar_amount,net_coins = email_coins.coins,app_version =app_version)
               user_history.save()
            except:
                pass
        try:
            print "gbgggggggg"
            user_login,created = UserClientLogin.objects.get_or_create(device = request.yoo['device'])
            print "gyuiyhyyuyy",user_login.id
            user_login.client_login = data['email']
            user_login.save()
        except:
            pass
        print "userr in home",user1.id
        coins_record = EmailCoins.objects.get(email=email)

        coins = coins_record.coins
        try:
            if user.device_coins_moved == False:
                print "dsssssssssssssssssssss"
                #device_coins = DeviceCoins.objects.filter(device_id__contains = request.META["HTTP_YOO_DEVICE_ID"])[0]
                device_coins = DeviceCoins.objects.filter(device_id = request.yoo['device'])[0]
                coins_record.coins = float(coins_record.coins) + float(device_coins.coins)
		device_coins.coins = float(device_coins.coins)
                amount = round((device_coins.coins)/1000,2)
                coins_record.dollar_amount = coins_record.dollar_amount + amount
		coins_record.coins = float(coins_record.coins)/10
                user.device_coins_moved =1
                user.save()
                coins_record.save()
                device_coins.coins = 0
                device_coins.save()
        except:
            pass

        try:
            preferences = user1.preferences
        except UserPreference.DoesNotExist:
            try:
                preferences = UserPreference(user=user1)
                preferences.save()
            except IntegrityError:
                preferences = user.preferences
        dollar_amount = coins_record.dollar_amount#coins/1000
	yoo_prize_code =  0
        yoo_game_code =  0
        ticket_req_check_coins = "0"
	old_app_version_android = ["7.19","7.20","7.21","7.22","7.23","7.24","7.25","7.26","7.27","7.28","7.29","7.30","7.31","7.32"]
        new_app_version_android = ["8.0","8.1","8.2","8.3","8.4","8.5","8.6","8.7","8.8","8.9","8.10"]
        old_app_version_iphone = ["7.10","7.11","7.12","7.13","7.14","7.15","7.16","7.17","7.18","7.19"]
        new_app_version_iphone = ["8.0","8.1","8.2","8.3","8.4","8.5","8.6","8.7","8.8","8.9","8.10"]
    	if (device_type=="ANDROID" and app_version in old_app_version_android) or (device_type=="IPHONE" and app_version in old_app_version_iphone):
            force_app_update = True
            cancel_app_update = False
        elif (app_version in new_app_version_android and device_type=="ANDROID") or (device_type=="IPHONE" and app_version in new_app_version_iphone):
            cancel_app_update = False
            force_app_update = False
        return {
        "coins": coins,
	"user_id":user.id,
	"force_app_update":force_app_update,
        "cancel_app_update":cancel_app_update,    
        "freeStuff":yoo_prize_code,
        "yoo_game":yoo_game_code,
	"dollar_exchange_rate":"100",
	"dollar_amount":dollar_amount,
    "physical_ticket_req_check_coins":ticket_req_check_coins,
         }

class LoginUser(View):
    @rest
    @Authenticate()
    def post(self,request):
        user_data = json.loads(request.body)
    
        email = user_data['email']
        password = user_data['password']
        user = None
        try:
           user = YooLottoUser.objects.get(email=email)
        except:
           raise exceptions.WebServiceException("This email Id is not registered with the Yoolotto")
        if user:
            if hashers.check_password(password, user.password):

                try:
                    user_details = UserDetails.objects.get(user=user)
                    phone = user_details.phone
                    address = user_details.address
                except:
                    phone = None
                    address = None
                
                ClientLoginRecord, created = UserClientLogin.objects.get_or_create(device=request.yoo['device'],defaults= {"client_login":email})
                                
                try:
                    UserTicketsRecord, created = LotteryTicketClient.objects.get_or_create(device=request.yoo['device'],defaults={"email":ClientLoginRecord.client_login})
                except:
                    pass
                
                
                yoo_user = request.yoo["user"]
                empty_string = ""
                return {"email":user.email,"user_name":user.name or empty_string,"phone":phone or empty_string,"address":address or empty_string,"id":user.id}
            else:
                raise exceptions.WebServiceException("Invalid Password")
            
                
        
        
    def _modify_email(self, user, email, password):
        # Search Others
        other = YooLottoUser.objects.filter(email=email)
        
        # Exclude current user
        if user:
            other = other.exclude(pk=user.pk)
        
        if not other:
            user.email = email
            
            if password:
                user.password = hashers.make_password(password)
            
            user.save()
            
            return
        
        other = other[0]
        if not other.password:
            self._merge(user, email, other)
            return
                                
        if not password:
            raise exceptions.WebServiceAuthorizationFailed("AUTH_REQUIRED")
        
        if hashers.check_password(password, other.password):
            self._merge(user, email, other)            
            return
        
        raise exceptions.WebServiceAuthorizationFailed("AUTH_INVALID")
        
    '''def _merge(self, user, email, other):
        from yoolotto.legacy.migration.tickets import MigrateTickets
        from yoolotto.legacy.models import Tickets as LegacyTicket, Users as LegacyUser
        
        # Import Data
    try:
            for legacy in LegacyUser.objects.filter(email=email):
                    MigrateTickets(legacy, user).run()
    except:
        pass
                
        # Users
        devices = user.devices.all()
        
        # Magic Here...
        for device in devices:
            device.user = other
            device.save()
            
        other.save()'''

class User(View):
    @rest
    @Authenticate()
    def get(self, request):
        """
        Retrieves the details of the currently logged in user, will create a 
        new user if the device is not identified
        """
        # Short-Circuit for Authentication Errors caused by invalid Device IDs
        if not request.yoo["user"] and request.yoo["auth"].get("__internal__reject__", False):
            raise exceptions.WebServiceAuthorizationFailed()
        print "reeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",request.yoo['device']
        if request.yoo["new_version"]:
            user = request.yoo["user"]
            wallet = user.get_wallet()
            plays = sum(map(lambda x: x.plays.count(), user.tickets.all()))
            from django.db.models import Sum
            try:
                preferences = user.preferences
            except UserPreference.DoesNotExist:
                try:
                    preferences = UserPreference(user=user)
                    preferences.save()
                except IntegrityError:
                    preferences = user.preferences
            try:
                ClientLoginRecord, created = UserClientLogin.objects.get_or_create(device=request.yoo['device'], defaults={'client_login':None})
            except:
                ClientLoginRecord = UserClientLogin.objects.filter(device=request.yoo['device'])[0]
                print "in filet client login"
            try:
                device_coins_record, created = DeviceCoins.objects.get_or_create(device_id=request.yoo['device'], defaults={'coins': 0})
            except:
                device_coins_record = DeviceCoins.objects.filter(device_id = request.yoo['device'])[0]
            if ClientLoginRecord.client_login:
                try:
                    coins_record, created = EmailCoins.objects.get_or_create(email=ClientLoginRecord.client_login, defaults={'coins': 0})
                except:
                    coins_record = EmailCoins.objects.filter(email=ClientLoginRecord.client_login)[0]
                coins = coins_record.get_coins() + device_coins_record.get_coins()

                tickets = LotteryTicketClient.objects.filter(email=ClientLoginRecord.client_login).count()
            else:
                print "in else"
                coins = device_coins_record.get_coins()
                tickets = LotteryTicketClient.objects.filter(device=request.yoo['device']).count()
            yoo_prize_code =  0
            print "yoooooooooooo",yoo_prize_code
            yoo_game_code =  0
            if request.yoo["new_version"]:
                #coins = wallet.coins
                print 11111111111111111111111111111111
                print "yo prize",yoo_prize_code
                return {
                   "email": user.email,
                   "password": True if user.password else False,
                   "tokens": dict([[token.name, token.token] for token in user.tokens.all()]),
                   "coins": coins,
                   "tickets": tickets,
                   "uncheckedTickets": sum(map(lambda x: x.plays.count(), user.tickets.filter(submissions__checked=False))),
                   "plays": plays,
                   "referral": user.referral,
                   "freeStuff":yoo_prize_code,
                   "yoo_game":yoo_game_code,
                   "preferences": {
                       "jackpot_drawing": preferences.jackpot_drawing,
                       "jackpot_frenzy": preferences.jackpot_frenzy,
                       "newsletter": preferences.newsletter
                    }}
        else:
        # Short-Circuit for Authentication Errors caused by invalid Device IDs
            if not request.yoo["user"] and request.yoo["auth"].get("__internal__reject__", False):
                raise exceptions.WebServiceAuthorizationFailed()
            user = request.yoo["user"]
            wallet = user.get_wallet()
            tickets = user.tickets.filter(plays__isnull=False).count()
            plays = sum(map(lambda x: x.plays.count(), user.tickets.all()))
            try:
                preferences = user.preferences
            except UserPreference.DoesNotExist:
                try:
                    preferences = UserPreference(user=user)
                    preferences.save()
                except IntegrityError:
                    preferences = user.preferences
            return {
                "email": user.email,
                "password": True if user.password else False,
                "tokens": dict([[token.name, token.token] for token in user.tokens.all()]),
                "coins": coins,
                "tickets": tickets,
                "uncheckedTickets": sum(map(lambda x: x.plays.count(), user.tickets.filter(submissions__checked=False))),
                "plays": plays,
                "referral": user.referral,
                "preferences": {
                    "jackpot_drawing": preferences.jackpot_drawing,
                    "jackpot_frenzy": preferences.jackpot_frenzy,
                    "newsletter": preferences.newsletter
                }
             }
    
    @rest
    @Authenticate(create=True)
    def post(self, request):
        """
        Updates the details of the currently logged in user
        """
        
        if request.yoo["new_version"]:
             if not request.yoo["user"] and request.yoo["auth"].get("__internal__reject__", False):
                raise exceptions.WebServiceAuthorizationFailed()
             user = request.yoo["user"]
             device = request.yoo["device"]
            
             try:
                data = json.loads(request.body)
             except:
                data = request.POST
             #print data['email']
                
             form = UserUpdateForm(data)
             if not form.is_valid():
                raise exceptions.WebServiceFormValidationFailed(form)

             email = form.cleaned_data["email"]
             password = form.cleaned_data["password"]
                
             # Routing Logic        
             '''if email and password:
                self._modify_email(user, email, password)
             elif email:
                self._modify_email(user, email, password=None)
             elif password:
                self._modify_password(user, password)'''
            
             existing = dict([[x.name, x] for x in user.tokens.all()])
            
             for key in ["fbToken", "twitterToken", "contestEmail", "requestedEmail"]:
                if key not in data:
                    continue
                
                if not form.cleaned_data[key]:
                    if key in existing:
                        existing[key].delete()
                else:
                    if key in existing:
                        existing[key].token = form.cleaned_data[key]
                    else:
                        existing[key] = UserToken(user=user, name=key, token=form.cleaned_data[key])
                
                    existing[key].save()
                    
             if "pushToken" in form.cleaned_data and form.cleaned_data["pushToken"]:
                request.yoo["device"].device_token = form.cleaned_data["pushToken"]
                request.yoo["device"].save()
                
             if "referral" in form.cleaned_data and form.cleaned_data["referral"]:
                user.referral = form.cleaned_data["referral"]
                user.save()

             if email:
                try:
                    coins_record, created = EmailCoins.objects.get_or_create(email=email,defaults={'coins': 0})
                except:
                    coins_record = EmailCoins.objects.filter(email=email)[0]
                coins_record.save()

            
             if user.password and user.email or user.tokens.filter(name="requestedEmail").exists():
                try:
                    CoinTicketGenericTransaction.objects.get(user=user, type="register")
                except CoinTicketGenericTransaction.DoesNotExist:
                    transaction = CoinTransaction(wallet=user.get_wallet())
                    transaction.save()
                    
                    _coins = CoinTicketGenericTransaction(user=user, type="register", transaction=transaction)
                    _coins.save()
                                    
                    transaction.amount = _coins.amount
                    transaction.save()
                try:
                    device_record = DeviceCoins.objects.filter(device_id=request.yoo['device'])[0]
                except:
                    device_record,created = DeviceCoins.objects.get_or_create(device_id=request.yoo['device'])
                device_record.coins = device_record.coins + float(_coins.amount)
                device_record.save()

             try:
                ClientLoginRecord, created = UserClientLogin.objects.get_or_create(device=request.yoo['device'], defaults={})
                print "in tryyy client login"
                print data
             except:
                ClientLoginRecord  = UserClientLogin.objects.filter(device=request.yoo['device'])
                print " in elseeeeeeeeeeeeeeeee"
             try:
                if data['password']:
                    for record in ClientLoginRecord:
                        record.client_login = email
                        record.save()
             except:
                try:
                    for record in ClientLoginRecord:
                        print "let see what happens"
                        record.client_login = data['user_email']
                        print "values of client login record",record.client_login
                        record.save()  
                except:
                    ClientLoginRecord.client_login = data['user_email']
                    ClientLoginRecord.save()
                 
             return self.get(request)
        else:
      
         # Short-Circuit for Authentication Errors caused by invalid Device IDs
             if not request.yoo["user"] and request.yoo["auth"].get("__internal__reject__", False):
                raise exceptions.WebServiceAuthorizationFailed()
            
             user = request.yoo["user"]
             device = request.yoo["device"]
            
             try:
                data = json.loads(request.body)
             except:
                data = request.POST
            
             form = UserUpdateForm(data)
             if not form.is_valid():
                raise exceptions.WebServiceFormValidationFailed(form)

             email = form.cleaned_data["email"]
             password = form.cleaned_data["password"]
                    
             # Routing Logic        
             if email and password:
                self._modify_email(user, email, password)
             elif email:
                self._modify_email(user, email, password=None)
             elif password:
                self._modify_password(user, password)
            
             existing = dict([[x.name, x] for x in user.tokens.all()])
            
             for key in ["fbToken", "twitterToken", "contestEmail", "requestedEmail"]:
                if key not in data:
                    continue
                
                if not form.cleaned_data[key]:
                    if key in existing:
                        existing[key].delete()
                else:
                    if key in existing:
                        existing[key].token = form.cleaned_data[key]
                    else:
                        existing[key] = UserToken(user=user, name=key, token=form.cleaned_data[key])
                
                    existing[key].save()
                    
             if "pushToken" in form.cleaned_data and form.cleaned_data["pushToken"]:
                request.yoo["device"].device_token = form.cleaned_data["pushToken"]
                request.yoo["device"].save()
                
             if "referral" in form.cleaned_data and form.cleaned_data["referral"]:
                user.referral = form.cleaned_data["referral"]
                user.save()
            
             if user.tokens.filter(name="requestedEmail").exists():
                try:
                    CoinTicketGenericTransaction.objects.get(user=user, type="register")
                except CoinTicketGenericTransaction.DoesNotExist:
                    transaction = CoinTransaction(wallet=user.get_wallet())
                    transaction.save()
                    
                    _coins = CoinTicketGenericTransaction(user=user, type="register", transaction=transaction)
                    _coins.save()
                                    
                    transaction.amount = _coins.amount
                    transaction.save()
            
             return self.get(request)
        
        def _modify_password(self, user, password):
            user.password = hashers.make_password(password)
            user.save()                
        
        def _modify_email(self, user, email, password):
            # Search Others
            other = YooLottoUser.objects.filter(email=email)
            
            # Exclude current user
            if user:
                other = other.exclude(pk=user.pk)
            
            if not other:
                user.email = email
                
                if password:
                    user.password = hashers.make_password(password)
                
                user.save()
                
                return
            
            other = other[0]
            if not other.password:
                self._merge(user, email, other)
                return
                                    
            if not password:
                raise exceptions.WebServiceAuthorizationFailed("AUTH_REQUIRED")
            
            if hashers.check_password(password, other.password):
                self._merge(user, email, other)            
                return
            
            raise exceptions.WebServiceAuthorizationFailed("AUTH_INVALID")
            
        def _merge(self, user, email, other):
            from yoolotto.legacy.migration.tickets import MigrateTickets
            from yoolotto.legacy.models import Tickets as LegacyTicket, Users as LegacyUser
            
            # Import Data
            try:
                for legacy in LegacyUser.objects.filter(email=email):
                        MigrateTickets(legacy, user).run()
            except:
                pass
            # Users
            devices = user.devices.all()
            
            # Magic Here...
            for device in devices:
                device.user = other
                device.save()
                
            other.save()        
        
class Preference(View):
    @rest
    @Authenticate()
    def get(self, request):
        # Short-Circuit for Authentication Errors caused by invalid Device IDs
        if not request.yoo["user"] and request.yoo["auth"].get("__internal__reject__", False):
            raise exceptions.WebServiceAuthorizationFailed()
        
        user = request.yoo["user"]
        
        try:
            preferences = user.preferences
        except UserPreference.DoesNotExist:
            preferences = UserPreference(user=user)
            preferences.save()
        
        return {
            "jackpot_drawing": preferences.jackpot_drawing,
            "jackpot_frenzy": preferences.jackpot_frenzy,
            "newsletter": preferences.newsletter
        }
    
    @rest
    @Authenticate(create=False)
    def post(self, request):
        # Short-Circuit for Authentication Errors caused by invalid Device IDs
        if not request.yoo["user"] and request.yoo["auth"].get("__internal__reject__", False):
            raise exceptions.WebServiceAuthorizationFailed()
        
        user = request.yoo["user"]
        
        try:
            data = json.loads(request.body)
        except:
            data = {}
        
        form = PreferenceUpdateForm(data)
        if not form.is_valid():
            raise exceptions.WebServiceFormValidationFailed(form)
        
        try:
            preferences = user.preferences
        except UserPreference.DoesNotExist:
            preferences = UserPreference(user=user)
            preferences.save()
            
#        for k, v in form.cleaned_data.iteritems():
#            print k, v, type(v)
                    
        preferences.jackpot_drawing = form.cleaned_data["jackpot_drawing"]
        preferences.jackpot_frenzy = form.cleaned_data["jackpot_frenzy"]
        preferences.newsletter = form.cleaned_data["newsletter"]
        
        preferences.save()
        
        return self.get(request)
    
    
class Device(View):
    @rest
    @Authenticate()
    def get(self, request):
        """
        
        
        """
        # Short-Circuit for Authentication Errors caused by invalid Device IDs
        if not request.yoo["user"] and request.yoo["auth"].get("__internal__reject__", False):
            raise exceptions.WebServiceAuthorizationFailed()
        
        device = request.yoo["device"]
        
        return {
            "type": device.device_type,
            "token": True if device.device_token else False
        }
        
    @rest
    @Authenticate(create=False)
    def post(self, request):
        # Short-Circuit for Authentication Errors caused by invalid Device IDs
        if not request.yoo["user"] and request.yoo["auth"].get("__internal__reject__", False):
            raise exceptions.WebServiceAuthorizationFailed()
        
        device = request.yoo["device"]
        
        try:
            data = json.loads(request.body)
        except:
            data = {}
        
        token = data.get("token", None)
        
        if not token:
            raise exceptions.WebServiceException("No Token Provided")
        
        existing = DeviceModel.objects.filter(device_token=token).exclude(pk=device.pk)
        for _existing in existing:
            _existing.device_token = None
            _existing.save()
        
        device.device_token = token
        device.save()
        
        return self.get(request)
    
class ReferralStats(View):
    @rest
    def get(self, request):
        if request.GET.get("token", None) != "j5nwvYbuIQflKSkUpetYh8OADJFXljvn":
            return HttpResponseNotFound()
        
        result = [["code", "count"],]
        data = YooLottoUser.objects.filter(referral__isnull=False).values('referral').annotate(Count('referral')).order_by("referral__count")
        map(lambda x: result.append([x["referral"], str(x["referral__count"])]), data)
        
        return HttpResponse(content="\n".join(map(lambda x: ", ".join(x), result)), content_type="text/csv")
        
class PlayStoreLink(View):
    @rest
    #@Authenticate()
    def get(self,request):
        from django.shortcuts import redirect
        from user_agents import parse
        ua_string = request.META['HTTP_USER_AGENT']
        print ua_string
        user_agent = parse(ua_string)
        user_agent_device = user_agent.os.family
        if user_agent_device == "Android":
	    play_store_link ="https://play.google.com/store/apps/details?id=com.yoolotto.android&hl=en"
        elif user_agent_device == "iOS":
	    play_store_link ="https://itunes.apple.com/in/app/yoolotto-complete-tasks-earn/id586408445?mt=8"
        return redirect(play_store_link)

class ReferralDetails(View):
    @rest
    @Authenticate()
    def post(self,request):
        device_type = request.META['HTTP_YOO_DEVICE_TYPE']
        app_version = request.META["HTTP_YOO_APP_VERSION"]
        user_data=get_decrypted_data(device_type,app_version,request.body)
        device_id = request.META['HTTP_YOO_DEVICE_ID']
        code = user_data['referral_code']
        email = request.META['HTTP_YOO_EMAIL_ID']
        if len(code)>0:
            assign_referral_coins(code,device_id,email)
        user = YooLottoUser.objects.get(email=email)
        play_store_link = "https://test.yoolotto.com/play_store"
        return {"play_store_link":play_store_link,"code":user.referral}

