from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from events.models import Venue, Event, Role
from tasks.models import Task
from common.models import SystemConfig

User = get_user_model()

class Command(BaseCommand):
    help = 'Load initial data for ISG 2026 Volunteer Management System'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading initial data...'))
        
        # Create users
        self.create_users()
        
        # Create events (first, since venues need events)
        self.create_events()
        
        # Create venues
        self.create_venues()
        
        # Create roles
        self.create_roles()
        
        # Create tasks
        self.create_tasks()
        
        # Create system config
        self.create_system_config()
        
        self.stdout.write(self.style.SUCCESS('Initial data loaded successfully!'))

    def create_users(self):
        self.stdout.write('Creating users...')
        
        # Admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@soi.org.au',
            defaults={
                'username': 'admin',
                'first_name': 'System',
                'last_name': 'Administrator',
                'user_type': 'ADMIN',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
                'country': 'Ireland',
                'preferred_language': 'en',
                'email_notifications': True,
                'sms_notifications': False,
                'gdpr_consent': True,
                'marketing_consent': False,
                'is_approved': True,
                'profile_complete': True,
                'email_verified': True,
                'phone_verified': False,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'  Created admin user: {admin_user.email}')
        
        # VMT Manager
        vmt_user, created = User.objects.get_or_create(
            email='vmt@soi.org.au',
            defaults={
                'username': 'vmt_manager',
                'first_name': 'VMT',
                'last_name': 'Manager',
                'user_type': 'VMT',
                'is_active': True,
                'is_staff': True,
                'is_superuser': False,
                'country': 'Ireland',
                'preferred_language': 'en',
                'email_notifications': True,
                'sms_notifications': False,
                'gdpr_consent': True,
                'marketing_consent': False,
                'is_approved': True,
                'profile_complete': True,
                'email_verified': True,
                'phone_verified': False,
            }
        )
        if created:
            vmt_user.set_password('vmt123')
            vmt_user.save()
            self.stdout.write(f'  Created VMT user: {vmt_user.email}')
        
        # Test volunteer
        volunteer_user, created = User.objects.get_or_create(
            email='volunteer@example.com',
            defaults={
                'username': 'test_volunteer',
                'first_name': 'Test',
                'last_name': 'Volunteer',
                'user_type': 'VOLUNTEER',
                'volunteer_type': 'GENERAL',
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'country': 'Ireland',
                'preferred_language': 'en',
                'email_notifications': True,
                'sms_notifications': False,
                'gdpr_consent': True,
                'marketing_consent': False,
                'is_approved': True,
                'profile_complete': False,
                'email_verified': True,
                'phone_verified': False,
            }
        )
        if created:
            volunteer_user.set_password('volunteer123')
            volunteer_user.save()
            self.stdout.write(f'  Created volunteer user: {volunteer_user.email}')

    def create_venues(self):
        self.stdout.write('Creating venues...')
        
        opening_ceremony = Event.objects.get(name='ISG 2026 Opening Ceremony')
        swimming_event = Event.objects.get(name='Swimming Competition - Day 1')
        
        # Brisbane Cricket Ground (Gabba)
        venue1, created = Venue.objects.get_or_create(
            name='Brisbane Cricket Ground (Gabba)',
            defaults={
                'event': opening_ceremony,
                'slug': 'gabba',
                'address_line_1': '411 Vulture Street, Woolloongabba',
                'city': 'Brisbane',
                'county': 'QLD',
                'postal_code': '4102',
                'country': 'Australia',
                'total_capacity': 42000,
                'venue_type': 'STADIUM',
                'wheelchair_accessible': True,
                'accessible_parking': True,
                'hearing_loop': True,
                'public_transport_access': 'Bus routes 200, 204, 206. Limited parking available. Wheelchair accessible entrances.',
                'contact_phone': '+61 7 3896 6166',
                'contact_email': 'info@thegabba.com.au',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(f'  Created venue: {venue1.name}')
        
        # Gold Coast Convention Centre
        venue2, created = Venue.objects.get_or_create(
            name='Gold Coast Convention Centre',
            defaults={
                'event': swimming_event,
                'slug': 'gccec',
                'address_line_1': '1 Gold Coast Highway, Broadbeach',
                'city': 'Gold Coast',
                'county': 'QLD',
                'postal_code': '4218',
                'country': 'Australia',
                'total_capacity': 6000,
                'venue_type': 'CONFERENCE_CENTER',
                'wheelchair_accessible': True,
                'accessible_parking': True,
                'accessible_toilets': True,
                'hearing_loop': True,
                'public_transport_access': 'G:link light rail to Broadbeach South. On-site parking available. Full wheelchair accessibility.',
                'contact_phone': '+61 7 5504 4000',
                'contact_email': 'info@gccec.com.au',
                'is_active': True
            }
        )
        if created:
            self.stdout.write(f'  Created venue: {venue2.name}')

    def create_events(self):
        self.stdout.write('Creating events...')
        
        admin_user = User.objects.get(email='admin@soi.org.au')
        vmt_user = User.objects.get(email='vmt@soi.org.au')
        
        # Opening Ceremony
        event1, created = Event.objects.get_or_create(
            name='ISG 2026 Opening Ceremony',
            defaults={
                'slug': 'isg-2026-opening-ceremony',
                'description': 'The grand opening ceremony for the Invictus Games 2026',
                'event_type': 'INTERNATIONAL_GAMES',
                'start_date': '2026-10-23',
                'end_date': '2026-10-23',
                'status': 'PLANNING',
                'host_city': 'Brisbane',
                'host_country': 'Australia',
                'volunteer_target': 500,
                'volunteer_minimum_age': 16,
                'created_by': admin_user
            }
        )
        if created:
            self.stdout.write(f'  Created event: {event1.name}')
        
        # Swimming Competition
        event2, created = Event.objects.get_or_create(
            name='Swimming Competition - Day 1',
            defaults={
                'slug': 'swimming-competition-day-1',
                'description': 'Swimming events for the Invictus Games 2026',
                'event_type': 'INTERNATIONAL_GAMES',
                'start_date': '2026-10-24',
                'end_date': '2026-10-24',
                'status': 'PLANNING',
                'host_city': 'Gold Coast',
                'host_country': 'Australia',
                'volunteer_target': 150,
                'volunteer_minimum_age': 18,
                'created_by': vmt_user
            }
        )
        if created:
            self.stdout.write(f'  Created event: {event2.name}')

    def create_roles(self):
        self.stdout.write('Creating roles...')
        
        opening_ceremony = Event.objects.get(name='ISG 2026 Opening Ceremony')
        swimming_event = Event.objects.get(name='Swimming Competition - Day 1')
        gabba_venue = Venue.objects.get(name='Brisbane Cricket Ground (Gabba)')
        gccec_venue = Venue.objects.get(name='Gold Coast Convention Centre')
        
        # Volunteer Coordinator
        role1, created = Role.objects.get_or_create(
            event=opening_ceremony,
            name='Volunteer Coordinator',
            defaults={
                'slug': 'volunteer-coordinator',
                'venue': gabba_venue,
                'role_type': 'COORDINATOR',
                'description': 'Coordinate and manage volunteers during the event',
                'minimum_age': 21,
                'total_positions': 10,
                'filled_positions': 0,
                'required_credentials': ['First Aid', 'Leadership Training'],
                'requires_garda_vetting': True,
                'uniform_required': True,
                'equipment_provided': ['radio', 'clipboard', 'hi-vis vest']
            }
        )
        if created:
            self.stdout.write(f'  Created role: {role1.name}')
        
        # Usher
        role2, created = Role.objects.get_or_create(
            event=opening_ceremony,
            name='Usher',
            defaults={
                'slug': 'usher',
                'venue': gabba_venue,
                'role_type': 'GENERAL_VOLUNTEER',
                'description': 'Guide attendees to their seats and provide assistance',
                'minimum_age': 16,
                'total_positions': 50,
                'filled_positions': 0,
                'required_credentials': [],
                'uniform_required': True,
                'equipment_provided': ['flashlight', 'program']
            }
        )
        if created:
            self.stdout.write(f'  Created role: {role2.name}')
        
        # Pool Deck Assistant
        role3, created = Role.objects.get_or_create(
            event=swimming_event,
            name='Pool Deck Assistant',
            defaults={
                'slug': 'pool-deck-assistant',
                'venue': gccec_venue,
                'role_type': 'GENERAL_VOLUNTEER',
                'description': 'Assist with pool deck operations during swimming events',
                'minimum_age': 18,
                'total_positions': 20,
                'filled_positions': 0,
                'required_credentials': ['Bronze Medallion', 'First Aid'],
                'uniform_required': True,
                'equipment_provided': ['stopwatch', 'towels', 'safety equipment']
            }
        )
        if created:
            self.stdout.write(f'  Created role: {role3.name}')

    def create_tasks(self):
        self.stdout.write('Creating tasks...')
        
        coordinator_role = Role.objects.get(name='Volunteer Coordinator')
        usher_role = Role.objects.get(name='Usher')
        
        # Coordinator Training Task
        task1, created = Task.objects.get_or_create(
            role=coordinator_role,
            title='Complete Volunteer Coordinator Training',
            defaults={
                'event': coordinator_role.event,
                'description': 'Complete the mandatory training module for volunteer coordinators',
                'task_type': 'CHECKBOX',
                'category': 'TRAINING',
                'is_mandatory': True,
                'due_date': '2026-09-01T23:59:59Z',
                'estimated_duration_minutes': 120,
                'instructions': 'Access the online training portal and complete all modules. Print certificate upon completion.',
                'task_configuration': {
                    'training_modules': ['Leadership Basics', 'Event Management', 'Emergency Procedures'],
                    'pass_mark': 80,
                    'certificate_required': True
                },
                'status': 'ACTIVE'
            }
        )
        if created:
            self.stdout.write(f'  Created task: {task1.title}')
        
        # Photo Upload Task
        task2, created = Task.objects.get_or_create(
            role=coordinator_role,
            title='Submit Profile Photo',
            defaults={
                'event': coordinator_role.event,
                'description': 'Upload a professional headshot for your volunteer ID badge',
                'task_type': 'PHOTO',
                'category': 'DOCUMENTATION',
                'is_mandatory': True,
                'due_date': '2026-09-15T23:59:59Z',
                'estimated_duration_minutes': 10,
                'instructions': 'Upload a clear, professional headshot photo. Photo should be passport-style with plain background.',
                'task_configuration': {
                    'photo_requirements': {
                        'format': ['JPEG', 'PNG'],
                        'max_size_mb': 5,
                        'min_resolution': '300x400',
                        'background': 'plain'
                    }
                },
                'status': 'ACTIVE'
            }
        )
        if created:
            self.stdout.write(f'  Created task: {task2.title}')
        
        # Venue Familiarization Task
        task3, created = Task.objects.get_or_create(
            role=usher_role,
            title='Venue Familiarization',
            defaults={
                'event': usher_role.event,
                'description': 'Complete venue walkthrough and familiarization checklist',
                'task_type': 'CHECKBOX',
                'category': 'PREPARATION',
                'is_mandatory': True,
                'due_date': '2026-10-20T23:59:59Z',
                'estimated_duration_minutes': 60,
                'instructions': 'Attend the venue walkthrough session and complete the familiarization checklist.',
                'task_configuration': {
                    'checklist_items': [
                        'Emergency exits located',
                        'Accessible facilities identified',
                        'Key personnel contacts noted',
                        'Seating layout understood'
                    ]
                },
                'status': 'ACTIVE'
            }
        )
        if created:
            self.stdout.write(f'  Created task: {task3.title}')

    def create_system_config(self):
        self.stdout.write('Creating system configuration...')
        
        configs = [
            {
                'key': 'volunteer_minimum_age',
                'value': '15',
                'description': 'Minimum age requirement for volunteers',
                'config_type': 'INTEGER'
            },
            {
                'key': 'justgo_api_timeout',
                'value': '30',
                'description': 'Timeout in seconds for JustGo API calls',
                'config_type': 'INTEGER'
            },
            {
                'key': 'email_notifications_enabled',
                'value': 'true',
                'description': 'Enable/disable email notifications system-wide',
                'config_type': 'BOOLEAN'
            }
        ]
        
        for config_data in configs:
            config, created = SystemConfig.objects.get_or_create(
                key=config_data['key'],
                defaults={
                    'value': config_data['value'],
                    'description': config_data['description'],
                    'config_type': config_data['config_type'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'  Created config: {config.key}') 