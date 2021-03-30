from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import pdb 




class SalesReportBySalesperson(models.TransientModel):
    _name = 'sale.salesperson.report'

    
    start_date = fields.Datetime(string="Start Date", required=True)
    end_date = fields.Datetime(string="End Date", required=True)
    salesperson_ids = fields.Many2many('res.users', string="Salesperson", required=True, domain=lambda self: [( "groups_id", "=", self.env.ref( "sales_team.group_sale_salesman" ).id ),('id','!=',2)]) 

    def print_sale_report_by_salesperson(self):
        sales_order = self.env['sale.order'].search([])
        sale_order_groupby_dict = {}
        for salesperson in self.salesperson_ids:
            #filtering sale orders by salesperson
            filtered_sale_order = list(filter(lambda x: x.user_id == salesperson, sales_order))
            # print('filtered_sale_order ===',filtered_sale_order)
            #filtering sale orders by date
            filtered_by_date = list(filter(lambda x: x.date_order >= self.start_date and x.date_order <= self.end_date, filtered_sale_order))
            sale_order_groupby_dict[salesperson.name] = filtered_by_date

        final_dist = {}
        for salesperson in sale_order_groupby_dict.keys():

            sale_data = []
            total_amount_untaxed = 0
            total_commission = 0
            temp_data2 = []
            target = 0
            for order in sale_order_groupby_dict[salesperson]:
                if(order.state == "sale"):
                    temp_data = []
                    target = order.target
                    subtotal = (order.amount_total - order.amount_tax)
                    commission  = round(subtotal * (order.commission_ratio / 100), 2)
                    
                    total_amount_untaxed += subtotal
                    total_commission += commission



                    temp_data.append(order.name)
                    temp_data.append(order.date_order)
                    temp_data.append(order.partner_id.name)
                    temp_data.append(round (subtotal, 2))
                    temp_data.append(commission)
                    temp_data.append(0)
                    temp_data.append(0)
                    temp_data.append(0)
                    sale_data.append(temp_data)

            
            if total_amount_untaxed < target:
                total_commission = 0      
            #pushing the last array to the 2d array containing the total values across all orders
            temp_data2.append(0)
            temp_data2.append(0)
            temp_data2.append(0)
            temp_data2.append(0)
            temp_data2.append(0)
            temp_data2.append(round(total_commission, 2))
            temp_data2.append(target)
            temp_data2.append(round(total_amount_untaxed, 2))
            sale_data.append(temp_data2)
            # print("output", sale_data)

            
            final_dist[salesperson] = sale_data
        datas = {
            'ids': self,
            'model': 'sale.salesperson.report',
            'form': final_dist,
            'start_date': self.start_date,
            'end_date': self.end_date
        }
        return self.env.ref('km_sales_report_by_salesperson.action_report_by_salesperson').report_action([], data=datas)
