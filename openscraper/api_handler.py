# -*- encoding: utf-8 -*-

import 	pprint
from 	pprint import pprint, pformat

import 	json
from 	bson import json_util, ObjectId
from 	boltons.iterutils import remap

from 	base_handler import *
from 	base_utils	import *



### TO DO 


### + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + ###
### API handlers as background tasks ########################################################
### + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + + ###

class APIrestHandler(BaseHandler): 
	"""
	main api point to get / query data from DB
	"""


	def retrieve_results(self):

		print 
		app_log.info("••• APIrestHandler.get ...\n")

		self.site_section = "api_paginated"

		# get current page - optionnal
		current_page = self.get_current_uri_without_error_slug()
		app_log.info("••• APIrestHandler.get / current_page : %s", current_page )



		### check user auth level 
		app_log.info("••• APIrestHandler.get / self.user_auth_level : %s ", self.user_auth_level )
		# --> open data level : "opendata", "commons", "collective", "admin"
		# check OPEN_LEVEL_DICT in settings_corefields.py for more infos
		# open_level = "opendata"
		# token = query_data["token"]
		# if token != None : 
		# 	# TO DO : check token to get corresponding opendata level 
		# 	open_level = "commons"
		### log query as warning if request allowed gets private or collective info
		open_level = self.user_auth_level_dict["data"] # generated by @check_request_token
		app_log.info("••• APIrestHandler.get / open_level : %s ", open_level )



		# get slug
		slug_ = self.request.arguments
		app_log.info("••• APIrestHandler.get / slug_ : \n %s", pformat(slug_) )

		# filter slug
		query_data = self.filter_slug( slug_, slug_class="data", query_from=self.site_section )
		app_log.info("••• APIrestHandler.get / query_data : \n %s ", pformat(query_data) )


		# TO DO : limit results 
		### override query_data["results_per_page"] if auth level doesn't allow it
		if open_level == "opendata" and query_data["results_per_page"] > QUERIES_MAX_RESULTS_IF_API :
			query_data["results_per_page"] = QUERIES_MAX_RESULTS_IF_API


		### TO DO : FACTORIZE WITH DataScrapedHandler HANDLER

		### retrieve datamodel from DB top make correspondances field's _id --> field_name
		# data_model_custom_cursor	 = self.application.coll_model.find({"field_class" : "custom", "is_visible" : True }) 
		# data_model_custom 			 = list(data_model_custom_cursor)
		# data_model_custom_dict 		 = { str(field["_id"])   : field for field in data_model_custom }
		# data_model_custom_dict_names = { field["field_name"] : field for field in data_model_custom }

		# data_model_core_cursor 		 = self.application.coll_model.find({"field_class" : "core" }) 
		# data_model_core 			 = list(data_model_core_cursor)
		# data_model_core_dict_names	 = { field["field_name"] : field for field in data_model_core }

		dm_set = self.get_datamodel_set()
		data_model_custom_list		 	= dm_set["data_model_custom_list"]
		data_model_custom_dict 		 	= dm_set["data_model_custom_dict"]
		data_model_custom_dict_names 	= dm_set["data_model_custom_dict_names"]
		data_model_core_list		 	= dm_set["data_model_core_list"]
		data_model_core_dict_names		= dm_set["data_model_core_dict_names"]

		### get spiders_list
		spiders_dict = self.get_spiders_infos(as_dict=True)
		app_log.info("••• APIrestHandler.get / spiders_dict : \n %s ", spiders_dict ) 

		### filter results depending on field's opendata level
		# get fields allowed
		allowed_fields_list, allowed_custom_fields, allowed_core_fields = self.get_authorized_datamodel_fields(open_level, data_model_custom_list, data_model_core_list )
		app_log.info("••• APIrestHandler.get / allowed_fields_list : \n %s ", allowed_fields_list ) 

		# get data 
		data, is_data, page_n_max, count_results_tot = self.get_data_from_query( 	query_data, 
																coll_name					 = "data", 
																query_from					 = self.site_section, 
																
																allowed_fields_list			 = allowed_fields_list,
																ignore_fields_list			 = ["_id"],
																
																data_model_custom_dict_names = data_model_custom_dict_names,
																data_model_core_dict_names	 = data_model_core_dict_names
															)
		# data, is_data, page_n_max = raw[0], raw[1], raw[3]
		app_log.info("••• APIrestHandler.get / is_data : %s ", is_data ) 

		
		
		### operations if there is data
		if is_data : 
			
			count_results = len(data)
			app_log.info("••• APIrestHandler.get / data[0] : \n %s " , pformat(data[0]) )
			
			### rewrite field names as understable ones --> replace field_oid by field_name 
			# cf : https://sedimental.org/remap.html
			data = remap( data, lambda p, k, v: ( data_model_custom_dict[k][u"field_name"], v) if k in data_model_custom_dict else (k, v))

		else :
			count_results = 0
			data = "no data for this query"


		### add header to tell user which level auth he/she gets to get
		full_json = { 
			
			"status" : "ok", 

			# header of the json with infos 
			"query_log" : {
				"_description"			: "synthesis of the query made by the user",

				"auth_level" 			: open_level ,
				"query"					: query_data ,
				"uri"					: self.request.uri ,

				# "page_n"				: count_results,
				"page_n_max"			: page_n_max,
				"count_results"			: count_results,
				"count_results_tot"		: count_results_tot,

				"fields_open_level" 	: [ 
											{ 	
												"field_name" : f["field_name"], 
												"field_open" : f["field_open"],
												"field_type" : f["field_type"]
											} for f in data_model_custom_list if f["field_open"] in OPEN_LEVEL_DICT[open_level]
										  ],
			},

			# infos about spiders
			"spiders_dict"				: spiders_dict,

			# data retrieved
			"query_results" 	 		: data
		} 

		return full_json


	@print_separate(APP_DEBUG)
	# @tornado.web.authenticated
	@check_request_token
	# @tornado.web.asynchronous
	# @gen.coroutine
	# @onthread
	def get(self, slug=None):
		""" main api point for app """

		# print 
		# app_log.info("••• APIrestHandler.get ...\n")

		# self.site_section = "api"

		# # get current page - optionnal
		# current_page = self.get_current_uri_without_error_slug()
		# app_log.info("••• APIrestHandler.get / current_page : %s", current_page )



		# ### check user auth level 
		# app_log.info("••• APIrestHandler.get / self.user_auth_level : %s ", self.user_auth_level )
		# # --> open data level : "opendata", "commons", "collective", "admin"
		# # check OPEN_LEVEL_DICT in settings_corefields.py for more infos
		# # open_level = "opendata"
		# # token = query_data["token"]
		# # if token != None : 
		# # 	# TO DO : check token to get corresponding opendata level 
		# # 	open_level = "commons"
		# ### log query as warning if request allowed gets private or collective info
		# open_level = self.user_auth_level_dict["data"] # generated by @check_request_token
		# app_log.info("••• APIrestHandler.get / open_level : %s ", open_level )



		# # get slug
		# slug_ = self.request.arguments
		# app_log.info("••• APIrestHandler.get / slug_ : \n %s", pformat(slug_) )

		# # filter slug
		# query_data = self.filter_slug( slug_, slug_class="data", query_from="api" )
		# app_log.info("••• APIrestHandler.get / query_data : \n %s ", pformat(query_data) )


		# # TO DO : limit results 
		# ### override query_data["results_per_page"] if auth level doesn't allow it
		# if open_level == "opendata" and query_data["results_per_page"] > QUERIES_MAX_RESULTS_IF_API :
		# 	query_data["results_per_page"] = QUERIES_MAX_RESULTS_IF_API


		# ### TO DO : FACTORIZE WITH DataScrapedHandler HANDLER

		# ### retrieve datamodel from DB top make correspondances field's _id --> field_name
		# # data_model_custom_cursor	 = self.application.coll_model.find({"field_class" : "custom", "is_visible" : True }) 
		# # data_model_custom 			 = list(data_model_custom_cursor)
		# # data_model_custom_dict 		 = { str(field["_id"])   : field for field in data_model_custom }
		# # data_model_custom_dict_names = { field["field_name"] : field for field in data_model_custom }

		# # data_model_core_cursor 		 = self.application.coll_model.find({"field_class" : "core" }) 
		# # data_model_core 			 = list(data_model_core_cursor)
		# # data_model_core_dict_names	 = { field["field_name"] : field for field in data_model_core }

		# dm_set = self.get_datamodel_set()
		# data_model_custom_list		 	= dm_set["data_model_custom_list"]
		# data_model_custom_dict 		 	= dm_set["data_model_custom_dict"]
		# data_model_custom_dict_names 	= dm_set["data_model_custom_dict_names"]
		# data_model_core_list		 	= dm_set["data_model_core_list"]
		# data_model_core_dict_names		= dm_set["data_model_core_dict_names"]


		# ### filter results depending on field's opendata level
		# # get fields allowed
		# allowed_fields_list, allowed_custom_fields, allowed_core_fields = self.get_authorized_datamodel_fields(open_level, data_model_custom_list, data_model_core_list )
		# app_log.info("••• APIrestHandler.get / allowed_fields_list : \n %s ", allowed_fields_list ) 

		# # get data 
		# data, is_data, page_n_max = self.get_data_from_query( 	query_data, 
		# 														coll_name					 = "data", 
		# 														query_from					 = self.site_section, 
																
		# 														allowed_fields_list			 = allowed_fields_list,
		# 														ignore_fields_list			 = ["_id"],
																
		# 														data_model_custom_dict_names = data_model_custom_dict_names,
		# 														data_model_core_dict_names	 = data_model_core_dict_names
		# 													)
		# # data, is_data, page_n_max = raw[0], raw[1], raw[3]
		# app_log.info("••• APIrestHandler.get / is_data : %s ", is_data ) 

		
		
		# ### operations if there is data
		# if is_data : 
			
		# 	count_results = len(data)
		# 	app_log.info("••• APIrestHandler.get / data[0] : \n %s " , pformat(data[0]) )
			
		# 	### rewrite field names as understable ones --> replace field_oid by field_name 
		# 	# cf : https://sedimental.org/remap.html
		# 	data = remap( data, lambda p, k, v: ( data_model_custom_dict[k][u"field_name"], v) if k in data_model_custom_dict else (k, v))

		# else :
		# 	count_results = 0
		# 	data = "no data for this query"


		# ### add header to tell user which level auth he/she gets to get
		# full_json = { 
			
		# 	"status" : "ok", 
		# 	# header of the json with infos 
		# 	"query_log" : {
		# 		"auth_level" 			: open_level ,
		# 		"query"					: query_data ,
		# 		"uri"					: self.request.uri ,
		# 		"count_results"			: count_results,
		# 		"fields_open_level" 	: [ 
		# 									{ 	
		# 										"field_name" : f["field_name"], 
		# 										"field_open" : f["field_open"],
		# 										"field_type" : f["field_type"]
		# 									} for f in data_model_custom_list if f["field_open"] in OPEN_LEVEL_DICT[open_level]
		# 								  ]
		# 	},
		# 	# data retrieved
		# 	"data_list" 	 	: data
		# } 

		full_json = self.retrieve_results()
		# full_json = { "status" : "ok", "sent" : self.retrieve_results() }

		### write data as json
		# cf : https://stackoverflow.com/questions/35083374/how-to-decode-a-unicode-string-python
		results = json.dumps(full_json, ensure_ascii=False, default=json_util.default).encode('utf8')

		print '.....\n' 

		self.write( results )
		# raise gen.Return(self.write( results ))
		
		self.finish()


	@print_separate(APP_DEBUG)
	@check_request_token
	def post(self, slug=None):

		### needs XSRF token to work
		### cf : 

		dic = tornado.escape.json_decode(self.request.body)
		app_log.info(dic)

		full_json = { "status" : "ok", "sent" : self.retrieve_results() }

		### write data as json
		# cf : https://stackoverflow.com/questions/35083374/how-to-decode-a-unicode-string-python
		results = json.dumps( full_json, ensure_ascii=False, default=json_util.default ).encode('utf8') 

		self.write( results )
		
		self.finish()