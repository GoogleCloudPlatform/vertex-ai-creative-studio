> ###### _This is not an officially supported Google product. This project is not eligible for the [Google Open Source Software Vulnerability Rewards Program](https://bughunters.google.com/open-source-security)._


# StoryCraft

An AI-powered video storyboard generation platform that transforms text descriptions into complete video narratives using Google's generative AI models. Create cinematic scenes, generate voiceovers, compose music, and export professional videos with a modern web interface.

## Description

StoryCraft leverages Google's [Imagen 4.0](https://ai.google.dev/models/imagen) for image generation, [Veo 3.0](https://ai.google.dev/models/veo) for video creation, [Chirp 3](https://ai.google.dev/models/chirp) for voice synthesis, and [Lyria 2](https://ai.google.dev/models/lyria) for music generation. The application provides a complete workflow from story concept to finished video, featuring a timeline-based editor for precise control over video composition.

## Interesting Techniques

- **Web Audio API Integration**: Real-time audio waveform visualization using [AudioContext](https://developer.mozilla.org/en-US/docs/Web/API/AudioContext) and [AnalyserNode](https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode) for dynamic audio analysis
- **FFmpeg Video Processing**: Server-side video concatenation, audio mixing, and overlay composition using [fluent-ffmpeg](https://github.com/fluent-ffmpeg/node-fluent-ffmpeg)
- **Timeline-Based Editing**: Custom drag-and-drop timeline interface with real-time preview and audio synchronization
- **Google Cloud Storage Integration**: Signed URL generation for secure media file access and storage
- **Exponential Backoff Retry Logic**: Robust error handling with jitter for AI API calls
- **CSS Custom Properties**: Dynamic theming system using [CSS custom properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties) for consistent design tokens

## Technologies & Libraries

- **[Next.js 15](https://nextjs.org/)** - React framework with App Router and server actions
- **[Google Vertex AI](https://cloud.google.com/vertex-ai)** - Imagen and Veo models for generative AI
- **[Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech)** - Neural voice synthesis
- **[TanStack Query](https://tanstack.com/query/latest)** - Server state management and caching
- **[Framer Motion](https://www.framer.com/motion/)** - Animation library for smooth UI transitions
- **[Radix UI](https://www.radix-ui.com/)** - Accessible component primitives
- **[Tailwind CSS](https://tailwindcss.com/)** - Utility-first CSS framework with custom design system
- **[DM Sans](https://fonts.google.com/specimen/DM+Sans)** - Google Fonts typography
- **[Lucide React](https://lucide.dev/)** - Icon library
- **[Sharp](https://sharp.pixelplumbing.com/)** - High-performance image processing
- **[UUID](https://github.com/uuidjs/uuid)** - Unique identifier generation

## Project Structure

```
storycraft/
├── app/                    # Next.js App Router pages and components
│   ├── actions/           # Server actions for AI generation and file operations
│   ├── api/              # API routes for scene and video endpoints
│   ├── components/       # React components organized by feature
│   │   ├── create/       # Story creation interface
│   │   ├── editor/       # Timeline-based video editor
│   │   ├── scenario/     # Story scenario management
│   │   ├── storyboard/   # Scene editing and management
│   │   ├── video/        # Video playback and export
│   │   └── ui/           # Reusable UI components
│   ├── fonts/            # Custom font files
│   └── globals.css       # Global styles and CSS variables
├── components/           # Shared UI components
├── lib/                  # Core utilities and external service integrations
├── public/               # Static assets including sample media files
│   ├── music/           # Background music tracks
│   ├── styles/          # Visual style reference images
│   ├── tts/             # Generated text-to-speech audio
│   └── uploads/         # User-uploaded content
└── Dockerfile           # Container configuration for deployment
```

**Key Directories:**
- [`app/actions/`](app/actions/) - Contains server actions for AI generation, video processing, and file management
- [`app/components/editor/`](app/components/editor/) - Houses the sophisticated timeline editor with audio visualization and real-time preview
- [`lib/`](lib/) - Core utilities including FFmpeg video processing, Google Cloud integrations, and AI model wrappers
- [`public/music/`](public/music/) - Curated background music library organized by mood and genre

## Deployment

StoryCraft can be deployed to [Google Cloud Run](https://cloud.google.com/run/docs/quickstarts/frameworks/deploy-nextjs-service) for scalable, serverless hosting. The application includes a `Dockerfile` for containerization and is optimized for Cloud Run's execution environment. To deploy:

1. Ensure you have the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and configured
2. Set up your Google Cloud project with the required APIs enabled (Vertex AI, Cloud Storage, Text-to-Speech)
3. Configure environment variables for your AI model endpoints and storage buckets
4. Deploy using the command: `gcloud run deploy --source .`

The application will automatically scale based on demand and only incur costs when actively processing video generation requests.
