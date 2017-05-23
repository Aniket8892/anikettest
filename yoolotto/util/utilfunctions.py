from yoolotto.rest.exceptions import WebServiceException
from yoolotto.user.cipher import androidDecryption,androidDecryptionsecurity,iOSdecryptionsecurity,iOSdecryption
from yoolotto.user.models import *
import json


def get_decrypted_data(device_type,app_version,request_data):
    iphone_version = ["8.0","8.1","8.2","8.3","8.4","8.5"]
    iphone_version_new = ["8.6","8.7","8.8","8.9","8.10"]
    android_version_new = ["8.6","8.7","8.8","8.9","8.10"]
    #print request_data
    if (device_type == "IPHONE" and app_version in iphone_version):
        decrypted_data = iOSdecryption(request_data)
        data = json.loads(decrypted_data)
    elif (device_type == "IPHONE" and app_version in iphone_version_new):
        decrypted_data = iOSdecryptionsecurity(request_data)
        data = json.loads(decrypted_data)
    elif (device_type == "ANDROID" and app_version in android_version_new):
        decrypted_data = androidDecryptionsecurity(request_data)
        data = json.loads(decrypted_data)
    else:
        raise exceptions.WebServiceException("Please update your app to continue earnings")
    #print "datsent",data
    return data

def get_country_object(code,name):
	try:
		country_obj = Country.objects.get(code__iexact=code,name__iexact=name,is_active = True)       
	except Exception as e:
		raise WebServiceException("This country does not have access to yoolotto.")
	return country_obj	


def get_or_create_country_object(code,name):
	try:
		country_obj = Country.objects.get(code__iexact=code,name__iexact=name)       
	except Exception as e:
		country_obj = Country.objects.create(code=code,name=name)
		pass
	return country_obj	


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    elif 'HTTP_X_REAL_IP' in request.META.keys():
        ip = request.META.get('HTTP_X_REAL_IP')
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# def get_decrypted_data(device_type,app_version,data,country=None):

# 	# if (device_type == "IPHONE" and float(app_version) in iphone_version):
# 	# 	decrypted_data = iOSdecryption(data)
# 	# 	data = json.loads(decrypted_data)
# 	# elif (device_type == "IPHONE" and app_version in iphone_version_new):
# 	# 	decrypted_data = iOSdecryptionsecurity(request.body)
# 	# 	data = json.loads(decrypted_data)
# 	# elif (device_type == "ANDROID" and app_version in android_version_new):
# 	# 	decrypted_data = androidDecryptionsecurity(request.body)
# 	# 	data = json.loads(decrypted_data)

# 	return decrypted_data    
    # else:
        #     data = json.loads(request.body)
        #     raise exceptions.WebServiceException("Please update your app to continue earnings")
ruels = {
	"IPHONE":{
		"dowla":"8.6",
		"yobux": "8.6",
		"cashout" : "8.6",
		"last_force_update":"8.2",
		"giftcard":"8.2"
		},
	"ANDROID":{
		"dowla":"8.6",
		"yobux": "8.6",
		"cashout" : "8.6",
		"last_force_update":"8.2",
		"giftcard":"8.2"
		}	
	}        

def get_actuall_active_list(version):
	version_restriction_dict_iphone = ruels['IPHONE']
	version_restriction_dict_android = ruels['ANDROID']
	version_list_iphone = AppVersionList.objects.filter(is_active = 1).values_list('version' , flat=True)
	version_list_android = AppVersionList.objects.filter(is_active = 1).values_list('version' , flat=True)






