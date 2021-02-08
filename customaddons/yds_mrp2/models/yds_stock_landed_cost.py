from odoo import models, fields, api, exceptions,_, tools
from odoo.exceptions import ValidationError
from datetime import datetime
from collections import defaultdict

class YdsStockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'


    def _check_sum(self):
        """ Check if each cost line its valuation lines sum to the correct amount
        and if the overall total amount is correct also """
        prec_digits = self.env.company.currency_id.decimal_places
        for landed_cost in self:
            total_amount = sum(landed_cost.valuation_adjustment_lines.mapped('additional_landed_cost'))
            diff = landed_cost.amount_total - total_amount
            print(total_amount)
            print(landed_cost.amount_total)
            # if not tools.float_is_zero(landed_cost.amount_total - total_amount, precision_digits=prec_digits):
            #     return False
            if diff > 0.1:
                return False


            val_to_cost_lines = defaultdict(lambda: 0.0)
            for val_line in landed_cost.valuation_adjustment_lines:
                val_to_cost_lines[val_line.cost_line_id] += val_line.additional_landed_cost
            print(val_to_cost_lines)
            if any((cost_line.price_unit - val_amount > 0.1)
                    for cost_line, val_amount in val_to_cost_lines.items()):
                return False
                # for cost_line, val_amount in val_to_cost_lines.items():
                #     if(cost_line.price_unit - val_amount > 0.1):
                #         return False
            
        return True