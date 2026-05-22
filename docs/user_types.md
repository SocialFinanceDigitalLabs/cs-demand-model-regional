# User Types

The Demand Model Regional WebApp is set up to have three user types.

All users must have MFA (Multi-Factor Authentication) enabled to access the application or admin panel.

1. **Standard Users**: 
Can create a forecast, save and load scenarios

2. **Admin Users**:
Has the same access as Standard Users, plus
Can upload data (if authenticated via SSO)
Can access the admin panel
Can add, edit, and remove users from the application
Can reset a users password

3. **Superusers**:
Has the same permissions and access as Admin Users, plus
Can view and manage all data within the application
Can promote other users to Admin or Superuser status
*We would expect a select number of superusers, who are part of the organisation responsible for the overall management and governance of the application.*

## User Management

Admin users (those that can upload data), should be managed via the SSO provider. We recommend using the SSO provider's user management features to create these users. Upon first sign in to the site via SSO, a Django user account will be automatically created for them. The user can then be added to the admin group within the application.
