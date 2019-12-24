# -*- coding: utf-8 -*-
from odoo import http

# class VitAssetsFiscalLinear(http.Controller):
#     @http.route('/vit_assets_fiscal_linear/vit_assets_fiscal_linear/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/vit_assets_fiscal_linear/vit_assets_fiscal_linear/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('vit_assets_fiscal_linear.listing', {
#             'root': '/vit_assets_fiscal_linear/vit_assets_fiscal_linear',
#             'objects': http.request.env['vit_assets_fiscal_linear.vit_assets_fiscal_linear'].search([]),
#         })

#     @http.route('/vit_assets_fiscal_linear/vit_assets_fiscal_linear/objects/<model("vit_assets_fiscal_linear.vit_assets_fiscal_linear"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('vit_assets_fiscal_linear.object', {
#             'object': obj
#         })