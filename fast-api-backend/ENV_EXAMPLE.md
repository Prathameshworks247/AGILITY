# Environment Variables

Create a `.env` file in the `fast-api-backend` directory with the following variables:

```env
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Next.js Backend URL (for forwarding reviews)
NEXTJS_API_URL=http://localhost:3000/api/task-reviews

# Service token shared with Next.js API (must match REVIEW_SERVICE_TOKEN)
NEXTJS_SERVICE_TOKEN=super-secret-token
```

## Required Variables

- `GEMINI_API_KEY`: Your Google Gemini API key for AI code reviews
- `NEXTJS_API_URL`: URL of your Next.js backend API endpoint (default: http://localhost:3000/api/task-reviews)
- `NEXTJS_SERVICE_TOKEN`: Shared secret for authenticating with the Next.js API

