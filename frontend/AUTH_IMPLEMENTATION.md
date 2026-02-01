# Authentication Implementation Summary

## Overview
This document describes the authentication and user management features added to the Text2DSL frontend.

## New Files Created

### Pages
- `src/pages/Login.jsx` - User login page with email/password form
- `src/pages/Register.jsx` - User registration page with validation
- `src/pages/UserProfile.jsx` - User profile management (edit profile, change password)
- `src/pages/AdminUsers.jsx` - Admin user management (super admin only)
- `src/pages/Chat.jsx` - Main chat interface (extracted from App.jsx)

### Components
- `src/components/ProtectedRoute.jsx` - Route wrapper for authentication checks
- `src/components/AppLayout.jsx` - Main app layout with navigation and user menu

### Hooks
- `src/hooks/useAuth.jsx` - Authentication context provider with login/logout/register methods

## Routes

### Public Routes
- `/login` - Login page
- `/register` - Registration page

### Protected Routes (require authentication)
- `/app` - Main chat interface
- `/app/review` - Review dashboard
- `/app/profile` - User profile settings
- `/app/admin/users` - User management (super admin only)

## Authentication Flow

1. **Login**: POST to `/api/v1/auth/token` with form data (OAuth2 format)
   - Stores JWT token in localStorage
   - Fetches current user info from `/api/v1/auth/me`

2. **Registration**: POST to `/api/v1/users/register` with user data
   - Redirects to login page on success

3. **Auto-login**: Checks localStorage for token on app load
   - Validates token by fetching user info
   - Redirects to login if invalid

4. **Protected Routes**: Uses ProtectedRoute component
   - Checks authentication status
   - Redirects to login if not authenticated
   - Can require admin role (`requireAdmin={true}`)

## API Integration

The frontend expects these backend endpoints:

### Authentication
- `POST /api/v1/auth/token` - Login (OAuth2 format: username=email&password=...)
- `GET /api/v1/auth/me` - Get current user info

### User Management
- `POST /api/v1/users/register` - Register new user
- `PUT /api/v1/users/me` - Update current user profile
- `PUT /api/v1/users/me/password` - Change password

### Admin Endpoints (super admin only)
- `GET /api/v1/admin/users` - List all users
- `POST /api/v1/admin/users` - Create new user
- `PUT /api/v1/admin/users/:id` - Update user

## Features

### Login Page
- Email/password form
- Error handling
- Loading states
- Link to registration
- Dark mode support

### Register Page
- Name, email, password fields
- Password confirmation
- Client-side validation (password length, matching)
- Success message with redirect
- Link to login

### User Profile Page
- View user info (name, email, role, status, join date)
- Edit profile (name, email)
- Change password (with current password verification)
- Role badges (Super Admin, Admin, User)
- Success/error feedback

### Admin Users Page
- List all users with search
- Create new users with role assignment
- Edit user details
- Activate/deactivate users
- Role management
- Super admin access control

### App Layout
- Navigation tabs (Chat, Review, Users)
- Dark mode toggle
- User menu with dropdown
  - Profile settings link
  - Sign out button
- Responsive design

## User Roles

1. **User** - Standard user with access to chat and review
2. **Admin** - Can access admin features (currently same as user)
3. **Super Admin** - Full access including user management

## Dark Mode

Dark mode preference is:
- Stored in localStorage
- Persists across sessions
- Applied globally with Tailwind CSS dark: classes
- Toggleable from header

## Security Features

- JWT token stored in localStorage
- Automatic token validation on load
- Protected routes with redirect to login
- Role-based access control
- Password requirements (8+ characters)
- Current password required for password change

## Styling

All components follow existing patterns:
- Tailwind CSS for styling
- lucide-react icons
- primary-500 color scheme
- Dark mode support with dark: prefix
- Consistent form layouts
- Loading states with spinners
- Error/success alerts

## Usage

1. Start the backend server (with authentication endpoints)
2. Run frontend: `npm run dev`
3. Navigate to `http://localhost:5173`
4. Default redirect to `/app` (will redirect to `/login` if not authenticated)
5. Register a new account or login with existing credentials
6. Access protected features after authentication

## Notes

- The admin endpoints need to be implemented on the backend
- JWT token expiration should be handled (currently relies on backend validation)
- Consider adding token refresh functionality for long sessions
- Super admin users can be created via direct database insertion or API endpoint
