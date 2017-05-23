from django.conf.urls import patterns, include, url

from yoolotto.reporting.views import *

urlpatterns = patterns('',
    #url(r'^graphs/$',PandasGraph.as_view()),
    #url(r'^pagination/$',PaginationCheck.as_view()),
    # url(r'^test/$',TestHtml.as_view()),
    url(r'^$',Home.as_view()),
    url(r'^suspect/$',SuspectedUsers.as_view()),
    #url(r'^filter/$',SuspectedUsersFilter.as_view()),
    url(r'^suspect/suspect_details_email/(?P<code>\w+)/$',SuspectedEmailDetails.as_view()),
    url(r'^suspect/suspect_details_device/(?P<code>\w+)/$',SuspectedDeviceDetails.as_view()),
    #url(r'^suspect/block_details/(?P<code>\w+)/$',BlockUser.as_view()),
    url(r'^suspect/block_details/$',BlockUser.as_view()),
    url(r'^logout/$',Logout.as_view()),
    #url(r'^block_details1/(?P<email>\w+)/(?P<device_id>\w+)/$',BlockUserDetails1.as_view()),
    #url(r'^suspect/block_user/(?P<device_id>\w+)/$',BlockUserViaDeviceId.as_view()),
)
