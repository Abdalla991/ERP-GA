from odoo import models, fields, api, _


class YDSStockMove(models.Model):
    _inherit = 'stock.move'

    qty_in_store = fields.Float(
        string=_("QTY. in Storage"), compute="_compute_qty_in_pre_production")

    @api.depends('product_id', 'picking_type_id')
    @api.onchange('product_id')
    def _compute_qty_in_pre_production(self):
        get_location = self.env['ir.config_parameter'].sudo(
        ).get_param("yds_mrp2.qty_in_store_id")
        for move in self:
            if move.picking_type_id.code == 'mrp_operation':
                qty = 0.0
                location_ids = self.env['stock.location'].browse(
                    [int(get_location)]).child_ids.ids.copy()
                location_ids.append(int(get_location))
                product_locations = self.env['stock.quant'].search([]).with_context(product_id=move.product_id).filtered(
                    lambda q: q.product_id == q._context['product_id']).location_id
                for location in product_locations:
                    if location.id in location_ids:
                        qty += self.env['stock.quant'].search([]).with_context(product_id=move.product_id).filtered(
                            lambda q: q.product_id == q._context['product_id'] and q.location_id.id == location.id).quantity
                move.qty_in_store = qty
