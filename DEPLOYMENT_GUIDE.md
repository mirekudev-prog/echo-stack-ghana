# ============================================
# DEPLOYMENT GUIDE FOR ECHOSTACK
# ============================================

## PREREQUISITES
1. Supabase account (for PostgreSQL database + storage)
2. Render/Railway account (for hosting) OR deploy locally
3. Resend account (optional, for email verification)
4. Paystack account (optional, for payments)

## STEP 1: SETUP SUPABASE DATABASE

### A. Create a new Supabase project
1. Go to https://supabase.com
2. Click "New Project"
3. Fill in project details and set a strong database password
4. Wait for project to initialize (~2 minutes)

### B. Get your database connection string
1. Go to Settings → Database
2. Under "Connection string", select "URI" tab
3. Copy the connection string (looks like: postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres)
4. IMPORTANT: Replace `[YOUR-PASSWORD]` with your actual database password

### C. Create storage bucket for uploads
1. Go to Storage in left sidebar
2. Click "New bucket"
3. Name it: `echostack-uploads`
4. Set to "Public" bucket
5. Click "Create bucket"

### D. Get API keys
1. Go to Settings → API
2. Copy these two values:
   - Project URL (e.g., https://xxxxx.supabase.co)
   - service_role key (NOT the anon key!)

## STEP 2: CONFIGURE ENVIRONMENT VARIABLES

### A. Create .env file
```bash
cp .env.example .env
```

### B. Edit .env with your values
Open `.env` and fill in:
- `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `ADMIN_SECRET`: Your admin password (change from default!)
- `DATABASE_URL`: Your Supabase connection string from Step 1B
- `SUPABASE_URL`: Your Supabase project URL from Step 1D
- `SUPABASE_SERVICE_KEY`: Your service_role key from Step 1D
- `RESEND_API_KEY`: (Optional) Get from https://resend.com/api-keys
- `PAYSTACK_SECRET_KEY`: (Optional) Get from Paystack dashboard

## STEP 3: INITIALIZE DATABASE

Run this command to create all tables:
```bash
python -c "from database import init_db; init_db()"
```

OR let the app auto-initialize on first run (tables are created automatically).

## STEP 4: TEST LOCALLY

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Visit http://localhost:8000 to test.

## STEP 5: DEPLOY TO RENDER

### Option A: Using render.yaml (recommended)
1. Push your code to GitHub
2. Go to https://render.com
3. Click "New +" → "Blueprint"
4. Connect your GitHub repository
5. Render will detect render.yaml and configure automatically
6. Add environment variables in Render dashboard:
   - DATABASE_URL (from Supabase)
   - SUPABASE_URL
   - SUPABASE_SERVICE_KEY
   - SECRET_KEY
   - ADMIN_SECRET
   - (Optional) RESEND_API_KEY, PAYSTACK_SECRET_KEY
7. Click "Apply" - deployment starts automatically

### Option B: Manual deployment
1. Push code to GitHub
2. In Render: New Web Service → Connect repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (same as above)
6. Deploy

## STEP 6: DEPLOY TO RAILWAY (alternative)

1. Push code to GitHub
2. Go to https://railway.app
3. New Project → Deploy from GitHub
4. Railway auto-detects Python
5. Add environment variables in Variables tab
6. Deploy

## STEP 7: POST-DEPLOYMENT

### A. Verify deployment
1. Visit your deployed URL
2. Test signup/login
3. Access admin dashboard at /admin
4. Upload a test file to verify Supabase storage

### B. Create admin user
1. Go to /admin
2. Enter your ADMIN_SECRET when prompted
3. You now have full access to no-code dashboard

### C. Configure custom domain (optional)
1. In Render/Railway, go to Settings → Domains
2. Add your custom domain
3. Update DNS records as instructed
4. Update BASE_URL in .env

## TROUBLESHOOTING

### Database connection errors
- Ensure DATABASE_URL has `?sslmode=require` at the end
- Check Supabase firewall settings (allow all IPs or add Render/Railway IPs)
- Verify password is correct in connection string

### File upload errors
- Ensure Supabase bucket is set to "Public"
- Verify SUPABASE_SERVICE_KEY (not anon key)
- Check bucket name matches SUPABASE_BUCKET variable

### Email not sending
- Verify domain in Resend dashboard
- Check RESEND_API_KEY is correct
- Ensure EMAIL_FROM uses verified domain

### Admin login not working
- Check ADMIN_SECRET matches in .env and what you're entering
- Clear browser cookies and try again

## SECURITY CHECKLIST

✅ Change ADMIN_SECRET from default
✅ Use strong SECRET_KEY (32+ random characters)
✅ Never commit .env to Git (it's in .gitignore)
✅ Use service_role key only on backend (never expose to frontend)
✅ Enable SSL/TLS for database (already configured)
✅ Set DEBUG=False in production

## SUPPORT

For issues:
1. Check application logs in Render/Railway dashboard
2. Review error messages in browser console
3. Verify all environment variables are set correctly
4. Test database connection locally first
