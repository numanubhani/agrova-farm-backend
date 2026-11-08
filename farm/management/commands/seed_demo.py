from django.core.management.base import BaseCommand

from farm.seed import seed_demo_data


class Command(BaseCommand):
    help = 'Load deterministic demo data (customers, deliveries, production, expenses, payments).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing data first.')

    def handle(self, *args, **options):
        seed_demo_data(reset=options['reset'])
        self.stdout.write(self.style.SUCCESS('Demo data loaded.'))
