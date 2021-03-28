
from odoo import models, fields, api, _

class UsersExtension(models.Model):
    _inherit = 'res.users'
    x_commission_ratio = fields.Float(string="Commission")
    x_target = fields.Float(string="Target")




class sale_extension(models.Model):
    _inherit="sale.order"
    # sale.order model has a reference to res.users, so there is no need to have a many2one field 
    commission_ratio = fields.Float('Sales commission', related='user_id.x_commission_ratio',readonly=False)
    target = fields.Float('Target', related='user_id.x_target',readonly=False)

class commission(models.Model):
    _name = "sale.commission"
    name = fields.Many2one('res.users',string='Salesperson', domain=lambda self: [( "groups_id", "=", self.env.ref( "sales_team.group_sale_salesman" ).id ),('id','!=',2)] ) 
    commission_ratio = fields.Float('Sales commission', related='name.x_commission_ratio',readonly=False)
    target = fields.Float('Target', related='name.x_target',readonly=False)
    _sql_constraints = [('sales_person_unique','unique(name)','selected sales person already have commission assigned')]

