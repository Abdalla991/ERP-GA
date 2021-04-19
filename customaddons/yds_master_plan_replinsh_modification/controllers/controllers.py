# -*- coding: utf-8 -*-
# from odoo import http


# class YdsMasterPlanReplinshModification/(http.Controller):
#     @http.route('/yds_master_plan_replinsh_modification//yds_master_plan_replinsh_modification//', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/yds_master_plan_replinsh_modification//yds_master_plan_replinsh_modification//objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('yds_master_plan_replinsh_modification/.listing', {
#             'root': '/yds_master_plan_replinsh_modification//yds_master_plan_replinsh_modification/',
#             'objects': http.request.env['yds_master_plan_replinsh_modification/.yds_master_plan_replinsh_modification/'].search([]),
#         })

#     @http.route('/yds_master_plan_replinsh_modification//yds_master_plan_replinsh_modification//objects/<model("yds_master_plan_replinsh_modification/.yds_master_plan_replinsh_modification/"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('yds_master_plan_replinsh_modification/.object', {
#             'object': obj
#         })
