# EchoStack Ghana - AI-Powered Heritage Platform

Ghana's Living Heritage Archive - AI Powered

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your configuration

# Run server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Visit http://localhost:8000

## 📦 Deployment

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for complete deployment instructions.

### Quick Deploy to Render
1. Push to GitHub
2. Connect repo in Render dashboard
3. Add environment variables from `.env.example`
4. Deploy automatically via `render.yaml`

## 🔑 Features

- **User Authentication**: Signup, login, email verification, password reset
- **Content Management**: Posts, stories, reels, archives
- **Admin Dashboard**: No-code site editor, theme customization, SEO settings
- **File Uploads**: Supabase storage integration
- **AI Integration**: Google Generative AI, Hugging Face models
- **Payments**: Paystack integration for premium subscriptions
- **Community**: Chat, following/subscribers system

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL (Supabase)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Storage**: Supabase Storage
- **Email**: Resend
- **Hosting**: Render/Railway ready

## 📁 Project Structure

```
echo-stack-ghana/
├── main.py              # FastAPI application & routes
├── models.py            # Database models
├── database.py          # Database configuration
├── requirements.txt     # Python dependencies
├── render.yaml          # Render deployment config
├── .env.example         # Environment variables template
├── DEPLOYMENT_GUIDE.md  # Complete deployment instructions
└── *.html               # Frontend pages
```

## 🔐 Admin Access

1. Visit `/admin`
2. Enter your ADMIN_SECRET (configured in .env)
3. Access no-code dashboard for:
   - Site editing
   - Theme & branding
   - SEO settings
   - User management
   - Analytics
   - Backup/Restore

## 📝 License

Private - All rights reserved

## 👤 Contact

For support, check the DEPLOYMENT_GUIDE.md troubleshooting section.
