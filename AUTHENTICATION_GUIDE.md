# Simple Password Authentication Implementation

I've successfully implemented a simple password-based authentication system for your Vertex AI Creative Studio project. Here's what was added:

## 🔧 Implementation Summary

### 1. Configuration (config/default.py)

- `SIMPLE_AUTH_ENABLED`: Enable/disable authentication (default: false)
- `SIMPLE_AUTH_PASSWORD`: The password users must enter (default: "demo123")
- `SESSION_TIMEOUT`: Session timeout in seconds (default: 24 hours)

### 2. Authentication Module (common/simple_auth.py)

- Password verification
- Route protection logic
- Session token management
- Cookie handling utilities

### 3. Application State (state/state.py)

- Added `is_authenticated` and `login_error` fields
- Authentication helper functions

### 4. Middleware (main.py)

- `simple_auth_middleware`: Protects all routes
- Returns 403 for API endpoints
- Redirects to /login for web pages

### 5. Login Page (pages/login.py)

- Clean, responsive login form
- Password input with error handling
- Automatic redirect after successful login

### 6. Authentication UI (common/auth_ui.py)

- Helper for showing logout buttons when auth is enabled
- Updated header components in pages

## 🚀 How to Enable

1. **Set Environment Variables:**

   ```bash
   export SIMPLE_AUTH_ENABLED=true
   export SIMPLE_AUTH_PASSWORD=your_secure_password
   ```

2. **Or create a `.env` file:**

   ```
   SIMPLE_AUTH_ENABLED=true
   SIMPLE_AUTH_PASSWORD=your_secure_password
   SESSION_TIMEOUT=86400
   ```

3. **Start the application:**
   ```bash
   python main.py
   ```

## 🔒 How It Works

### When Authentication is Enabled:

1. **All routes are protected** except:

   - `/login` (login page)
   - `/api/login` and `/api/logout` (auth endpoints)
   - Static files (`/static/`, `/assets/`, `/favicon.ico`)

2. **Unauthenticated users** accessing any protected route:

   - **Web pages**: Redirected to `/login`
   - **API endpoints**: Receive 403 Forbidden

3. **Login Process:**

   - User enters password on `/login` page
   - Password is verified against `SIMPLE_AUTH_PASSWORD`
   - Authentication cookie is set for valid sessions
   - User is redirected to `/home`

4. **Logout Process:**
   - Click logout button in header (when auth is enabled)
   - Authentication cookie is cleared
   - User is redirected to `/login`

### When Authentication is Disabled:

- All routes are accessible without authentication
- Login page still exists but is not enforced
- No logout buttons are shown

## ✨ Features

- **Simple Setup**: Just set environment variables
- **Session Management**: Secure cookie-based sessions
- **Responsive Design**: Clean login form that matches the app theme
- **Error Handling**: Clear error messages for failed login attempts
- **Logout Support**: Logout buttons in page headers
- **Route Protection**: Comprehensive protection for all routes
- **API Support**: Proper 403 responses for API endpoints

## 📝 Usage Examples

### Enable Authentication

```bash
export SIMPLE_AUTH_ENABLED=true
export SIMPLE_AUTH_PASSWORD=mySecurePassword123
python main.py
```

### Test the Implementation

1. Start the app with authentication enabled
2. Visit `http://localhost:8080/` - you'll be redirected to `/login`
3. Enter the correct password - you'll be redirected to `/home`
4. Try accessing `/about` or any other route - access granted
5. Try accessing `/api/some-endpoint` without auth - receive 403
6. Click logout button - redirected back to `/login`

## 🔐 Security Notes

- Passwords are verified in plaintext (suitable for simple demo purposes)
- For production, consider using hashed passwords
- Sessions are cookie-based with configurable timeout
- All authentication logic is centralized and easy to modify
- HTTPS is recommended for production deployments

## 📂 Files Modified/Created

### New Files:

- `common/simple_auth.py` - Authentication logic
- `pages/login.py` - Login page component
- `common/auth_ui.py` - UI helpers
- `.env.auth.example` - Configuration example

### Modified Files:

- `config/default.py` - Added auth configuration
- `state/state.py` - Added auth state management
- `main.py` - Added middleware and login API
- `components/header.py` - Added logout button support
- `pages/about.py` - Added logout button
- `pages/home.py` - Added logout button

The implementation is complete and ready to use! 🎉
