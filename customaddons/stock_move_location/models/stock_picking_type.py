# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    show_move_onhand = fields.Boolean(
        string="Show Move On hand stock",
        help="Show a button 'Move On Hand' in the Inventory Dashboard "
        "to initiate the process to move the products in stock "
        "at the origin location.",
    )

    def action_move_location(self):
        action = self.env.ref(
            "stock_move_location.wiz_stock_move_location_action"
        ).read()[0]
        action["context"] = {
            "default_origin_location_id": self.default_location_src_id.id,
            "default_destination_location_id": self.default_location_dest_id.id,
            "default_picking_type_id": self.id,
            "default_edit_locations": False,
        }
        return action


class YDSStockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        if self.picking_type_id.code == 'internal':

            for move_line in self.move_line_ids_without_package:
                yds_product_id=move_line.product_id
                yds_stock_location=move_line.location_id
                res=self.env['stock.quant'].search([('location_id','=',yds_stock_location.id),('product_id','=',yds_product_id.id)])
                final_number= res.quantity-res.reserved_quantity
                if move_line.qty_done > final_number:
                    raise ValidationError("Done quantity can not be bigger than stock available quantity")
                else:
                    super(YDSStockPicking,self).button_validate()
