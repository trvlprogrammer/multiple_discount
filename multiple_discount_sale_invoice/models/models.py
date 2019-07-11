from odoo import models, fields, api
from odoo.exceptions import Warning

class discountDiscount(models.Model):
    _name           = 'discount.discount'
    _description    = 'model discount for sales and invoicing'
    
    name            = fields.Char(string = 'Discount Name')
    amount          = fields.Float(string = 'Discount amount')
    discount_type   = fields.Selection([('fixed_amount','Fixed Amount'),('percentage','Percentage')],string = 'Discount Type')
    
    
    @api.model
    def create(self,vals):
        if vals['amount'] == 0 :
            raise Warning('Discount amount can not be 0')        
        return super(discountDiscount,self).create(vals)
    
    
    @api.multi
    def write(self,vals):
        if vals.has_key('amount'):
            if vals['amount'] == 0 :
                raise Warning('Discount amount can not be 0')
        return super(discountDiscount,self).write(vals)
    
    
class saleOrderLine(models.Model):
    _inherit        = 'sale.order.line'
    
    multiple_discounts  = fields.Many2many('discount.discount','discount_sales_rel','order_id','discount_id', string = 'Discounts')
    type                = fields.Selection([('fixed_amount','Fixed Amount'),('percentage','Percentage')],string = 'Type')
     
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'multiple_discounts','type')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit
            if line.multiple_discounts : 
                discounts = line.multiple_discounts
                if line.type == 'percentage' :
                   for discount in discounts :                         
                       price = price * (1 - (discount.amount) / 100.0)
                elif line.type == 'fixed_amount' :
                    for discount in discounts :                         
                       price = price - discount.amount
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            
                         
    @api.model 
    def create(self,vals):
        if vals.has_key('multiple_discounts'):
            for disc in vals['multiple_discounts'][0][2] :
                if self.env['discount.discount'].browse(disc).discount_type != vals['type']:
                    raise Warning('Type and discount type has to be match')
                 
        return super(saleOrderLine,self).create(vals)
    
    
    @api.multi 
    def write(self,vals):
        type = self.type
        if vals.has_key('type') :
            type = vals['type']         
        if vals.has_key('multiple_discounts'):
            for disc in vals['multiple_discounts'][0][2] :
                if self.env['discount.discount'].browse(disc).discount_type != type:
                    raise Warning('Type and discount type has to be match')                 
        elif vals.has_key('type'):
            for disc in vals['multiple_discounts'][0][2] :
                if self.env['discount.discount'].browse(disc).discount_type != vals['type']:
                    raise Warning('Type and discount type has to be match')                    
        return super(saleOrderLine,self).write(vals)         
        
        
class AccountInvoiceLine(models.Model):
    _inherit            = "account.invoice.line"
    
    multiple_discounts  = fields.Many2many('discount.discount','discount_invoice_rel','invoice_id','discount_id', string = 'Discounts')
    type                = fields.Selection([('fixed_amount','Fixed Amount'),('percentage','Percentage')],string = 'Type')

        
    @api.model 
    def create(self,vals):
        if vals.has_key('multiple_discounts'):
            for disc in vals['multiple_discounts'][0][2] :
                if self.env['discount.discount'].browse(disc).discount_type != vals['type']:
                    raise Warning('Type and discount type has to be match')                 
        return super(AccountInvoiceLine,self).create(vals)
      
    
    @api.multi 
    def write(self,vals):
        type = self.type
        if vals.has_key('type') :
            type = vals['type']
        if vals.has_key('multiple_discounts'):
            for disc in vals['multiple_discounts'][0][2] :
                if self.env['discount.discount'].browse(disc).discount_type != type:
                    raise Warning('Type and discount type has to be match')
        return super(AccountInvoiceLine,self).write(vals)
     
    
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
        'invoice_id.date_invoice', 'invoice_id.date','type','multiple_discounts')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        for line in self:
            price = line.price_unit
            if line.multiple_discounts : 
                discounts = line.multiple_discounts
                
                if line.type == 'percentage' :
                   for discount in discounts :                         
                       price = price * (1 - (discount.amount) / 100.0)
                       
                elif line.type == 'fixed_amount' :
                    for discount in discounts :                         
                       price = price - discount.amount        
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        self.price_total = taxes['total_included'] if taxes else self.price_subtotal
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.with_context(date=self.invoice_id._get_currency_rate_date()).compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
        
        
class AccountInvoiceInherit(models.Model):
    _inherit = "account.invoice"
    
    
    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        round_curr = self.currency_id.round
        for line in self.invoice_line_ids:
            price_unit = line.price_unit
            if line.multiple_discounts : 
                discounts = line.multiple_discounts                
                if line.type == 'percentage' :
                   for discount in discounts :                         
                       price_unit = price_unit * (1 - (discount.amount) / 100.0)                       
                elif line.type == 'fixed_amount' :
                    for discount in discounts :                         
                       price_unit = price_unit - discount.amount
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)
                if key not in tax_grouped:
                    tax_grouped[key] = val
                    tax_grouped[key]['base'] = round_curr(val['base'])
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += round_curr(val['base'])
        return tax_grouped
    
    
    
class SaleOrderInherit(models.Model):
    _inherit = "sale.order"
    
    
    @api.multi
    def _get_tax_amount_by_group(self):
        self.ensure_one()
        res = {}
        for line in self.order_line:
            price_reduce = line.price_unit
            if line.multiple_discounts : 
                discounts = line.multiple_discounts                
                if line.type == 'percentage' :
                   for discount in discounts :                         
                       price_reduce = price_reduce * (1 - (discount.amount) / 100.0)                       
                elif line.type == 'fixed_amount' :
                    for discount in discounts :                         
                       price_reduce = price_reduce - discount.amount
            taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id, partner=self.partner_shipping_id)['taxes']
            for tax in line.tax_id:
                group = tax.tax_group_id
                res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                for t in taxes:
                    if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                        res[group]['amount'] += t['amount']
                        res[group]['base'] += t['base']
        res = sorted(res.items(), key=lambda l: l[0].sequence)
        res = [(l[0].name, l[1]['amount'], l[1]['base'], len(res)) for l in res]
        return res

    