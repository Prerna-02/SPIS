# SPIS Auth System

## Overview

Authentication gate for SPIS with:
- Password-based login (required)
- Optional face verification using FaceNet
- JWT tokens in httpOnly cookies
- Protected route middleware

## Quick Start

### 1. Start PostgreSQL

```bash
cd e:\DL_Final_Project\db
docker compose up -d postgres
```

Wait for postgres to be healthy, then manually run schema:
```bash
docker exec -i spis-postgres psql -U spis_user -d spis < init/01_schema.sql
docker exec -i spis-postgres psql -U spis_user -d spis < init/02_views.sql
```

### 2. Start Auth Service

```bash
cd e:\DL_Final_Project\services\auth
pip install -r requirements.txt
python -m uvicorn app:app --reload --port 8004
```

### 3. Start Frontend

```bash
cd e:\DL_Final_Project\frontend
npm run dev
```

### 4. Access

- Frontend: http://localhost:3000
- You will be redirected to /login
- Register a new account or login

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create new user |
| `/auth/login` | POST | Login (password + optional face) |
| `/auth/logout` | POST | Clear session cookie |
| `/auth/me` | GET | Get current user |
| `/auth/face/enroll` | POST | Save face embedding |
| `/auth/face/verify` | POST | Test face verification |

## Face Recognition

### Enroll Face (after registration)
1. Login to your account
2. Send POST to `/auth/face/enroll` with:
```json
{
  "face_image": "data:image/jpeg;base64,..."
}
```

### Verify Face (during login)
1. Enter username + password
2. Click "Add Face Verification"
3. Capture your face
4. Submit login - face will be verified against stored embedding

### Similarity Threshold
- Default: 0.6 (60% similarity required)
- Configure via `FACE_SIMILARITY_THRESHOLD` env var
- Higher = more strict, lower = more lenient

## Files Structure

```
services/auth/
├── app.py          # FastAPI endpoints
├── auth.py         # Password hashing + JWT
├── face.py         # FaceNet embeddings
├── db.py           # Postgres connection
├── config.py       # Environment config
├── requirements.txt
├── Dockerfile
└── .env.example

frontend/
├── middleware.ts           # Route protection
├── app/
│   ├── login/page.tsx      # Login page
│   ├── register/page.tsx   # Register page
│   └── components/
│       ├── WebcamCapture.tsx
│       └── LogoutButton.tsx
```

## Environment Variables

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=spis
POSTGRES_USER=spis_user
POSTGRES_PASSWORD=spis_dev_password

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_EXPIRE_HOURS=24

# Face Recognition
FACE_SIMILARITY_THRESHOLD=0.6
FACE_REQUIRED=false  # If true, face must pass for login
```

## Security Notes

- Passwords hashed with bcrypt (12 rounds)
- JWT stored in httpOnly cookie (not accessible to JS)
- Face embeddings only - no raw images stored
- Token expires after 24 hours
