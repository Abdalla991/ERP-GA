from odoo import models, fields, api, exceptions,_
from odoo.exceptions import ValidationError
from collections import defaultdict
import ipdb 
from datetime import datetime

class YdsMrpProduction(models.Model):
    _inherit = "mrp.production"
    yds_extra_cost = fields.Float(string="Extra Cost",readonly=True, Default=0.0,store=True)
    yds_saved_cost = fields.Float(string="Cost Savings",readonly=True, Default=0.0,store=True)
    yds_expected_cost = fields.Float(string="Expected Cost", readonly=True, Default=0.0,store=True)
    yds_actual_cost = fields.Float(string="Actual Cost", readonly=True, Default=0.0,store=True)
    
    def yds_calc_extra_cost(self):
        for production in self:
            production.yds_expected_cost = 0.0
            production.yds_actual_cost = 0.0
            production.yds_saved_cost= 0.0
            production.yds_extra_cost = 0.0

            #calculate actual cost
            for mo_line in production.move_raw_ids:
                    line_cost = mo_line.product_id.standard_price*mo_line.quantity_done
                    print(line_cost)
                    production.yds_actual_cost += line_cost
            if production.bom_id :
                #calculate expected cost
                print("Product: "+ production.product_id.name +" has a bom")
                for bom_line in production.bom_id.bom_line_ids:
                    line_cost=(bom_line.product_qty*bom_line.product_id.standard_price)/production.bom_id.product_qty
                    print(line_cost)
                    production.yds_expected_cost += line_cost*production.product_qty
                print("Expected Cost= "+ str(production.yds_expected_cost))
                print("Actual Cost= "+ str(production.yds_actual_cost) )

                #Calculate extra and saved costs
                if production.yds_expected_cost > production.yds_actual_cost :
                    production.yds_saved_cost = production.yds_expected_cost - production.yds_actual_cost
                elif production.yds_expected_cost < production.yds_actual_cost :
                    production.yds_extra_cost = production.yds_actual_cost - production.yds_expected_cost

#     #remove subcontracting extra cost field from measres/filters/groupby..
#     @api.model
#     def fields_get(self, fields=None):
#         #Fields to be added in Filters/Group By
#         show = ['extra_cost']
#         res = super(YdsMrpProduction, self).fields_get()
#         #True = add fields, False = Remove fields
#         for field in show:
#             res[field]['selectable'] = False
#             res[field]['sortable'] = False
#             res[field]['exportable'] = False # to hide in export list
#             res[field]['store'] = False
#         return res




class YDSMrpCostStructure(models.AbstractModel):
    _inherit = 'report.mrp_account_enterprise.mrp_cost_structure'

    def get_lines(self, productions):
        ProductProduct = self.env['product.product']
        StockMove = self.env['stock.move']
        res = []
        for product in productions.mapped('product_id'):
            mos = productions.filtered(lambda m: m.product_id == product)
            total_cost = 0.0

            # Get operations details + cost
            operations = []
            Workorders = self.env['mrp.workorder'].search([('production_id', 'in', mos.ids)])
            if Workorders:
                query_str = """SELECT wo.id, op.id, wo.name, partner.name, sum(t.duration), wc.costs_hour
                                FROM mrp_workcenter_productivity t
                                LEFT JOIN mrp_workorder wo ON (wo.id = t.workorder_id)
                                LEFT JOIN mrp_workcenter wc ON (wc.id = t.workcenter_id)
                                LEFT JOIN res_users u ON (t.user_id = u.id)
                                LEFT JOIN res_partner partner ON (u.partner_id = partner.id)
                                LEFT JOIN mrp_routing_workcenter op ON (wo.operation_id = op.id)
                                WHERE t.workorder_id IS NOT NULL AND t.workorder_id IN %s
                                GROUP BY wo.id, op.id, wo.name, wc.costs_hour, partner.name, t.user_id
                                ORDER BY wo.name, partner.name
                            """
                self.env.cr.execute(query_str, (tuple(Workorders.ids), ))
                for wo_id, op_id, wo_name, user, duration, cost_hour in self.env.cr.fetchall():
                    operations.append([user, op_id, wo_name, duration / 60.0, cost_hour])

            # Get the cost of raw material effectively used
            raw_material_moves = []
            query_str = """SELECT
                                sm.product_id,
                                mo.id,
                                abs(SUM(svl.quantity)),
                                abs(SUM(svl.value))
                             FROM stock_move AS sm
                       INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                       LEFT JOIN mrp_production AS mo on sm.raw_material_production_id = mo.id
                            WHERE sm.raw_material_production_id in %s AND sm.state != 'cancel' AND sm.product_qty != 0 AND scrapped != 't'
                         GROUP BY sm.product_id, mo.id"""
            self.env.cr.execute(query_str, (tuple(mos.ids), ))
            for product_id, mo_id, qty, cost in self.env.cr.fetchall():
                raw_material_moves.append({
                    'qty': qty,
                    'cost': cost,
                    'product_id': ProductProduct.browse(product_id),
                })
                total_cost += cost

            # Get the cost of scrapped materials
            scraps = StockMove.search([('production_id', 'in', mos.ids), ('scrapped', '=', True), ('state', '=', 'done')])
            uom = mos and mos[0].product_uom_id
            mo_qty = 0
            if any(m.product_uom_id.id != uom.id for m in mos):
                uom = product.uom_id
                for m in mos:
                    qty = sum(m.move_finished_ids.filtered(lambda mo: mo.state == 'done' and mo.product_id == product).mapped('product_uom_qty'))
                    if m.product_uom_id.id == uom.id:
                        mo_qty += qty
                    else:
                        mo_qty += m.product_uom_id._compute_quantity(qty, uom)
            else:
                for m in mos:
                    mo_qty += sum(m.move_finished_ids.filtered(lambda mo: mo.state == 'done' and mo.product_id == product).mapped('product_uom_qty'))
            for m in mos:
                byproduct_moves = m.move_finished_ids.filtered(lambda mo: mo.state != 'cancel' and mo.product_id != product)
            res.append({
                'mos':mos,
                'product': product,
                'mo_qty': mo_qty,
                'mo_uom': uom,
                'operations': operations,
                'currency': self.env.company.currency_id,
                'raw_material_moves': raw_material_moves,
                'total_cost': total_cost,
                'scraps': scraps,
                'mocount': len(mos),
                'byproduct_moves': byproduct_moves
            })
        return res

        
# class StockMove(models.Model):
#     _inherit = "stock.move"
#     forecast_availability = fields.Float('Forecast Availability', compute='_compute_forecast_information', digits='Product Unit of Measure',store=True )

#     @api.depends('product_id', 'picking_type_id', 'picking_id', 'reserved_availability', 'priority', 'state', 'product_uom_qty', 'location_id')
#     def _compute_forecast_information(self):
#         """ Compute forecasted information of the related product by warehouse."""
#         self.forecast_availability = False
#         self.forecast_expected_date = False

#         not_product_moves = self.filtered(lambda move: move.product_id.type != 'product')
#         for move in not_product_moves:
#             move.forecast_availability = move.product_qty

#         product_moves = (self - not_product_moves)
#         warehouse_by_location = {loc: loc.get_warehouse() for loc in product_moves.location_id}

#         outgoing_unreserved_moves_per_warehouse = defaultdict(lambda: self.env['stock.move'])
#         for move in product_moves:
#             picking_type = move.picking_type_id or move.picking_id.picking_type_id
#             is_unreserved = move.state in ('waiting', 'confirmed', 'partially_available')
#             if picking_type.code in self._consuming_picking_types() and is_unreserved:
#                 outgoing_unreserved_moves_per_warehouse[warehouse_by_location[move.location_id]] |= move
#             elif picking_type.code in self._consuming_picking_types():
#                 move.forecast_availability = move.reserved_availability

#         for warehouse, moves in outgoing_unreserved_moves_per_warehouse.items():
#             if not warehouse:  # No prediction possible if no warehouse.
#                 continue
#             product_variant_ids = moves.product_id.ids
#             wh_location_ids = [loc['id'] for loc in self.env['stock.location'].search_read(
#                 [('id', 'child_of', warehouse.view_location_id.id)],
#                 ['id'],
#             )]
#             ForecastedReport = self.env['report.stock.report_product_product_replenishment']
#             forecast_lines = ForecastedReport.with_context(warehouse=warehouse.id)._get_report_lines(None, product_variant_ids, wh_location_ids)
#             for move in moves:
#                 lines = [l for l in forecast_lines if l["move_out"] == move._origin and l["replenishment_filled"] is True]
#                 if lines:
#                     move.forecast_availability = sum(m['quantity'] for m in lines)
#                     move_ins_lines = list(filter(lambda report_line: report_line['move_in'], lines))
#                     if move_ins_lines:
#                         expected_date = max(m['move_in'].date for m in move_ins_lines)
#                         move.forecast_expected_date = expected_date