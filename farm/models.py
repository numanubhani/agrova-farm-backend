from django.db import models


class Farm(models.Model):
    """Singleton settings row for the farm."""
    name = models.CharField(max_length=120, default='Demo Dairy Farm')

    def __str__(self):
        return self.name

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Customer(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True, default='')
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Usual daily quantity (L)')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Delivery(models.Model):
    """One customer's milk quantity delivered on one date."""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='deliveries')
    date = models.DateField()
    liters = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = [('customer', 'date')]
        ordering = ['-date']

    def __str__(self):
        return f'{self.customer} {self.date} {self.liters}L'


class Production(models.Model):
    """Morning / evening milk production totals for one date."""
    date = models.DateField(unique=True)
    am = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pm = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.date} am={self.am} pm={self.pm}'


CATEGORY_CHOICES = [
    ('Chara (Feed)', 'Chara (Feed)'),
    ('Wanda / Khal', 'Wanda / Khal'),
    ('Medicine / Doctor', 'Medicine / Doctor'),
    ('Labour Salary', 'Labour Salary'),
    ('Bijli', 'Bijli'),
    ('Diesel / Transport', 'Diesel / Transport'),
    ('Maintenance', 'Maintenance'),
    ('Other', 'Other'),
]


class Expense(models.Model):
    date = models.DateField()
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default='Other')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.date} {self.category} {self.amount}'


class Payment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.customer} {self.date} {self.amount}'
