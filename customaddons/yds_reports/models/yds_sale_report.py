# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class YDSProductTemplates(models.Model):
    _inherit = "product.template"

    # #By default odoo does not store the product's cost, we have to create a new field containing the cost and store it
    # standard_price = fields.Float(
    #     'Cost', compute='_compute_standard_price',
    #     inverse='_set_standard_price', search='_search_standard_price',
    #     digits='Product Price', groups="base.group_user",
    #     help="""In Standard Price & AVCO: value of the product (automatically computed in AVCO).
    #     In FIFO: value of the last unit that left the stock (automatically computed).
    #     Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
    #     Used to compute margins on sale orders.""",store=True)


class YDSSaleReport(models.Model):
    _inherit = "sale.report"

    # x_price_total = fields.Float('YDS Total', readonly=True)
    x_price_subtotal_wo_uni = fields.Float('Sale Price', readonly=True)
    cost = fields.Float('Cost', readonly=True)
    cost_percentage = fields.Float('Cost %', readonly=True)
    uni_amount = fields.Float('Universal Discount Amount', readonly=True)
    uni_rate = fields.Float('Universal Discount %', readonly=True)
    customer_tag = fields.Char('Customer Tag', readonly=True)

    # def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
    #     # fields['price_total'] = ", SUM(l.x_price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS price_total"
    #     # fields['price_subtotal'] = ", SUM(l.x_price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS price_subtotal"
    #     fields['x_price_subtotal'] = ", SUM(l.x_price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS x_price_subtotal"
    #     fields['cost'] = ", CASE WHEN l.product_id IS NOT NULL THEN sum(t.standard_price * l.product_uom_qty) ELSE 0 END as cost"
    #     fields['uni_amount'] = ", CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_subtotal - l.x_price_subtotal) ELSE 0 END AS uni_amount"
    #     # fields['cost_percentage'] = ", CASE WHEN l.product_id IS NOT NULL THEN sum((t.standard_price / l.price_unit / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END))ELSE 0 END as cost_percentage"
    #     return super(YDSSaleReport, self)._query(with_clause, fields, groupby, from_clause)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            coalesce(min(l.id), -s.id) as id,
            l.product_id as product_id,
            t.uom_id as product_uom,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as product_uom_qty,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_delivered / u.factor * u2.factor) ELSE 0 END as qty_delivered,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_invoiced / u.factor * u2.factor) ELSE 0 END as qty_invoiced,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_to_invoice / u.factor * u2.factor) ELSE 0 END as qty_to_invoice,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.x_price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as price_total,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.x_price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as price_subtotal,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.yds_untaxed_amount_to_invoice / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as untaxed_amount_to_invoice,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.yds_untaxed_amount_invoiced / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as untaxed_amount_invoiced,
            count(*) as nbr,
            s.name as name,
            s.date_order as date,
            s.state as state,
            s.partner_id as partner_id,
            s.user_id as user_id,
            s.company_id as company_id,
            s.campaign_id as campaign_id,
            s.medium_id as medium_id,
            s.source_id as source_id,
            extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
            t.categ_id as categ_id,
            s.pricelist_id as pricelist_id,
            s.analytic_account_id as analytic_account_id,
            s.team_id as team_id,
            p.product_tmpl_id,
            partner.country_id as country_id,
            partner.industry_id as industry_id,
            partner.commercial_partner_id as commercial_partner_id,
            CASE WHEN l.product_id IS NOT NULL THEN sum(p.weight * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as weight,
            CASE WHEN l.product_id IS NOT NULL THEN sum(p.volume * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as volume,
            l.discount as discount,
            CASE WHEN l.product_id IS NOT NULL THEN sum((l.price_unit * l.product_uom_qty * l.discount / 100.0 / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END))ELSE 0 END as discount_amount,
            s.id as order_id,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_subtotal - l.x_price_subtotal) ELSE 0 END AS uni_amount,
            l.yds_product_cost as cost,
            l.yds_cost_percentage as cost_percentage,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.x_price_subtotal_wo_uni / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as x_price_subtotal_wo_uni,
            s.ks_global_discount_rate as uni_rate,
            s.yds_customer_tag as customer_tag
        """
        # CASE WHEN l.product_id IS NOT NULL THEN sum((t.standard_price * l.product_uom_qty / NULLIF(SUM(l.x_price_subtotal_wo_uni),0))*100/ CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as cost_percentage,
        for field in fields.values():
            select_ += field

        from_ = """
                sale_order_line l
                      right outer join sale_order s on (s.id=l.order_id)
                      join res_partner partner on s.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join uom_uom u on (u.id=l.product_uom)
                    left join uom_uom u2 on (u2.id=t.uom_id)
                    left join product_pricelist pp on (s.pricelist_id = pp.id)
                %s
        """ % from_clause

        groupby_ = """
            l.product_id,
            l.order_id,
            t.uom_id,
            t.categ_id,
            s.name,
            s.date_order,
            s.partner_id,
            s.user_id,
            s.state,
            s.company_id,
            s.campaign_id,
            s.medium_id,
            s.source_id,
            s.pricelist_id,
            s.analytic_account_id,
            s.team_id,
            p.product_tmpl_id,
            partner.country_id,
            partner.industry_id,
            partner.commercial_partner_id,
            l.discount,
            l.yds_cost_percentage,
            l.yds_product_cost,
            l.yds_cost_percentage,
            s.yds_customer_tag,
            s.id %s
        """ % (groupby)

        return '%s (SELECT %s FROM %s GROUP BY %s)' % (with_, select_, from_, groupby_)