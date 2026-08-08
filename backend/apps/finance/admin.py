from django.contrib import admin

from apps.finance.models import (
    Account,
    AccountMapping,
    AccountingEvent,
    BankReconciliation,
    BankStatementLine,
    BusinessUnit,
    CostCenter,
    FinancialPeriod,
    FiscalYear,
    JournalEntry,
    JournalLine,
    PostingRule,
    PostingRuleLine,
    SupplierPayment,
)

admin.site.register(Account)
admin.site.register(BusinessUnit)
admin.site.register(CostCenter)
admin.site.register(JournalEntry)
admin.site.register(JournalLine)
admin.site.register(AccountMapping)
admin.site.register(AccountingEvent)
admin.site.register(FiscalYear)
admin.site.register(FinancialPeriod)
admin.site.register(PostingRule)
admin.site.register(PostingRuleLine)
admin.site.register(SupplierPayment)
admin.site.register(BankReconciliation)
admin.site.register(BankStatementLine)
