# SOI Hub Admin Documentation

## Table of Contents

1. [Getting Started](#getting-started)
2. [User Management](#user-management)
3. [Volunteer Management](#volunteer-management)
4. [Event Management](#event-management)
5. [Task Management](#task-management)
6. [Reporting & Analytics](#reporting--analytics)
7. [System Administration](#system-administration)
8. [Mobile Admin Interface](#mobile-admin-interface)
9. [Troubleshooting](#troubleshooting)
10. [Security & Permissions](#security--permissions)

---

## Getting Started

### Accessing the Admin Interface

The SOI Hub admin interface is accessible at:
- **Development**: `http://127.0.0.1:8000/admin/`
- **Production**: `https://195.7.35.202/admin/`

### Login Credentials

Use your assigned admin credentials to log in. If you don't have credentials, contact the IT team at `it@specialolympics.ie`.

### Dashboard Overview

Upon login, you'll see the main dashboard with:
- **Real-time Statistics**: Key performance indicators and metrics
- **Recent Activity**: Latest system activities and changes
- **Quick Actions**: Shortcuts to common administrative tasks
- **Alerts**: Important notifications and system status updates

### Navigation

The admin interface is organized into the following sections:
- **Authentication and Authorization**: User and group management
- **Accounts**: User profiles and permissions
- **Events**: Event, venue, and role management
- **Volunteers**: Volunteer profiles and EOI submissions
- **Tasks**: Task assignment and completion tracking
- **Integrations**: JustGo API and external system management
- **Reporting**: Analytics and report generation
- **Common**: System configuration and audit logs

---

## User Management

### User Types and Roles

The system supports multiple user types with different permission levels:

1. **Admin**: Full system access and configuration
2. **GOC (Games Organizing Committee)**: High-level event management
3. **CVT (Competition Venue Team)**: Venue-specific management
4. **VMT (Volunteer Management Team)**: Volunteer coordination
5. **Staff**: General administrative access
6. **Volunteer**: Limited access to personal profile and tasks

### Managing Users

#### Creating New Users

1. Navigate to **Accounts > Users**
2. Click **Add User**
3. Fill in required information:
   - Username (unique identifier)
   - Email address
   - First and last name
   - User type
   - Password
4. Set additional details as needed
5. Click **Save**

#### User Approval Process

New volunteer registrations require approval:

1. Go to **Accounts > Users**
2. Filter by "Pending Approval" status
3. Review user details and EOI submission
4. Click on the user to view full profile
5. Use **Approve** or **Reject** actions
6. Add approval notes if required

#### Bulk Operations

For managing multiple users:

1. Select users using checkboxes
2. Choose from bulk actions:
   - **Approve selected users**
   - **Send notification emails**
   - **Export user data**
   - **Update user status**

### User Profile Management

#### Viewing User Profiles

- Click on any username to view detailed profile
- Review personal information, contact details, and preferences
- Check verification status (email, phone)
- View activity history and login records

#### Editing User Information

- Use the **Change** button to edit user details
- Update contact information, addresses, emergency contacts
- Modify user type or volunteer category as needed
- Save changes and review audit log

---

## Volunteer Management

### Expression of Interest (EOI) System

#### Managing EOI Submissions

1. Navigate to **Volunteers > EOI Submissions**
2. View all volunteer applications with status indicators
3. Filter by submission status, volunteer type, date range, sports preferences

#### EOI Review Process

For each submission review:
1. **Profile Information**: Personal details, contact info, demographics
2. **Recruitment Preferences**: Sports, venues, roles, availability
3. **Games Information**: Photo, uniform details, dietary requirements
4. **Corporate Group**: If applicable, group affiliation

#### EOI Actions

- **Approve**: Convert EOI to active volunteer profile
- **Reject**: Decline application with reason
- **Request More Info**: Send follow-up questions
- **Export Data**: Generate reports for review

### Volunteer Profiles

#### Profile Management

1. Go to **Volunteers > Volunteer Profiles**
2. View comprehensive volunteer information:
   - Personal details and contact information
   - Skills, experience, and qualifications
   - Availability and preferences
   - Training status and certifications
   - Background check status
   - JustGo integration status

#### Status Management

Track volunteer status through lifecycle:
- **Pending**: Awaiting approval
- **Active**: Approved and available
- **Training**: Undergoing required training
- **Qualified**: Fully trained and certified
- **Inactive**: Temporarily unavailable
- **Suspended**: Access restricted

#### JustGo Integration

For volunteers with JustGo membership:
- View membership details and credentials
- Sync data between systems
- Validate qualifications against role requirements
- Handle credential updates and renewals

### Corporate Volunteer Groups

#### Managing Corporate Groups

1. Navigate to **Volunteers > Corporate Volunteer Groups**
2. View registered corporate partners
3. Manage group details:
   - Organization information
   - Contact person details
   - Group size and preferences
   - Special requirements

#### Group Operations

- **Add volunteers** to corporate groups
- **Assign group coordinators**
- **Schedule group activities**
- **Generate group reports**

---

## Event Management

### Events

#### Creating Events

1. Go to **Events > Events**
2. Click **Add Event**
3. Configure event details including name, dates, venue, capacity
4. Set status and visibility options

### Venues

#### Venue Management

1. Navigate to **Events > Venues**
2. Add or edit venue information including address, capacity, facilities
3. Configure venue-specific settings and requirements

### Roles

#### Role Definition

1. Go to **Events > Roles**
2. Create or modify roles:
   - Role name and description
   - Required qualifications
   - Capacity limits
   - Skill requirements
   - Training prerequisites

#### Role Requirements

Set specific requirements:
- **Age restrictions**
- **Physical capabilities**
- **Certifications needed**
- **Experience level**
- **Language skills**

### Assignments

#### Managing Volunteer Assignments

1. Navigate to **Events > Assignments**
2. View current assignments with status
3. Create new assignments:
   - Select volunteer
   - Choose event and role
   - Set dates and times
   - Add special instructions

#### Assignment Status Tracking

Monitor assignment lifecycle:
- **Pending**: Awaiting volunteer confirmation
- **Confirmed**: Volunteer accepted
- **Checked In**: Volunteer arrived
- **Completed**: Assignment finished
- **No Show**: Volunteer didn't attend
- **Cancelled**: Assignment cancelled

#### Admin Overrides

For special circumstances:
- Override qualification requirements
- Modify capacity limits
- Emergency assignments
- Last-minute changes

---

## Task Management

### Task Types

The system supports:
- **Checkbox**: Simple completion tasks
- **Photo**: Tasks requiring photo evidence
- **Text**: Tasks requiring text responses
- **Custom**: Specialized task types

### Task Assignment

#### Creating Tasks

1. Go to **Tasks > Tasks**
2. Click **Add Task**
3. Configure task details, type, requirements, and dependencies

#### Role-Specific Tasks

Assign tasks based on volunteer roles:
- **Training tasks** for new volunteers
- **Certification tasks** for specific roles
- **Event-specific tasks** for assignments
- **Ongoing tasks** for regular volunteers

### Task Completion

#### Monitoring Progress

1. Navigate to **Tasks > Task Completions**
2. View completion status across all tasks
3. Filter by:
   - Volunteer
   - Task type
   - Completion status
   - Date range

#### Verification Process

For tasks requiring verification:
- Review submitted evidence
- Approve or reject completions
- Provide feedback to volunteers
- Track verification history

### Task Analytics

#### Performance Metrics

Monitor task completion rates:
- **Overall completion rates**
- **Task-specific performance**
- **Volunteer engagement levels**
- **Time to completion**

#### Reporting

Generate task reports for:
- Training compliance
- Role readiness
- Performance analysis
- Resource planning

---

## Reporting & Analytics

### Dashboard Analytics

The dashboard provides real-time metrics and KPIs including:
- Total volunteers and breakdown by type
- Active events and capacity utilization
- Task completion rates
- System health indicators

### Report Generation

Available reports include:
1. **Volunteer Summary Report**
2. **Event Summary Report**
3. **Venue Utilization Report**
4. **Training Status Report**

### PowerBI Integration

#### Analytics Endpoints

Access advanced analytics through PowerBI:
- **Volunteer analytics** with demographic breakdowns
- **Event performance** with attendance tracking
- **Operational metrics** with efficiency measures
- **Predictive analytics** for planning

#### Data Export

Export data for external analysis:
- **JSON format** for API integration
- **CSV format** for spreadsheet analysis
- **Excel format** with formatting
- **Custom datasets** for specific needs

---

## System Administration

### Admin Overrides

1. Go to **Common > Admin Overrides**
2. View active and historical overrides
3. Create new overrides for special circumstances
4. Monitor override usage and compliance

### Audit Logging

All administrative actions are logged for security and compliance.

### System Configuration

#### Content Management

Manage system content:
- **FAQ entries** for user support
- **Venue information** for public display
- **System announcements** and notifications
- **Help documentation** updates

#### System Settings

Configure system behavior:
- **Email notifications** settings
- **Integration parameters** for external systems
- **Security policies** and restrictions
- **Performance optimization** settings

---

## Mobile Admin Interface

The mobile admin interface provides:
- Responsive design for all screen sizes
- Touch-optimized controls
- Quick actions for common tasks
- Real-time updates during events

### Mobile Features

#### Dashboard

- **Real-time statistics** with mobile-friendly widgets
- **Activity feed** with pull-to-refresh
- **Quick action buttons** for common tasks
- **Notification center** for alerts

#### Volunteer Management

- **Search and filter** volunteers
- **View volunteer profiles** with key information
- **Approve/reject** applications
- **Send notifications** to volunteers

#### Event Management

- **Event overview** with status indicators
- **Assignment management** for events
- **Check-in/check-out** functionality
- **Real-time updates** during events

### Mobile Best Practices

- **Use landscape mode** for data-heavy screens
- **Enable notifications** for important updates
- **Sync regularly** when online
- **Use quick actions** for efficiency

---

## Troubleshooting

### Common Issues

#### Login Problems
- Verify username and password
- Check account approval status
- Clear browser cache
- Contact IT support if issues persist

#### Performance Issues
- Check internet connection
- Clear browser cache
- Use filters to limit data displayed

#### Data Sync Issues

**Issue**: JustGo data not syncing
**Solutions**:
1. Check integration status in admin
2. Verify API credentials
3. Review sync logs for errors
4. Manually trigger sync if needed
5. Contact IT for API issues

### Error Messages

#### Common Error Codes

- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource doesn't exist
- **500 Server Error**: System error, contact IT
- **ValidationError**: Data validation failed

#### Getting Help

1. **Check this documentation** first
2. **Review audit logs** for error details
3. **Contact IT support** at `it@specialolympics.ie`
4. **Provide error details** and steps to reproduce
5. **Include screenshots** if helpful

---

## Security & Permissions

### User Permissions

Each user type has specific permission levels from full admin access to limited volunteer self-service capabilities.

### Security Best Practices

- Use strong passwords
- Log out when finished
- Don't share credentials
- Report security concerns immediately

### Data Privacy

#### GDPR Compliance

The system follows GDPR requirements:
- **Consent management** for data processing
- **Right to access** personal data
- **Right to rectification** of incorrect data
- **Right to erasure** when appropriate
- **Data portability** for users

#### Data Handling

- **Minimize data collection** to necessary information
- **Secure data storage** with encryption
- **Limited data retention** periods
- **Controlled data access** based on roles
- **Regular data audits** for compliance

---

## Support and Contact Information

### IT Support

- **Email**: `it@specialolympics.ie`
- **Hours**: Monday-Friday, 9:00 AM - 5:00 PM

### Documentation Updates

This documentation is regularly updated. For the latest version:
- Check the admin interface help section
- Visit the SOI Hub documentation portal
- Contact IT for specific questions

### Training and Resources

- **New user training** sessions available
- **Video tutorials** for common tasks
- **Best practices guides** for each role
- **Regular updates** on new features

---

*Last updated: December 2024*
*Version: 1.0*
*SOI Hub Admin Documentation* 