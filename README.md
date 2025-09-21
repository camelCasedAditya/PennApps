# PennApps Project — How It Works

This repository combines two complementary systems:

1) CourseAI (Django): an AI-assisted learning platform that turns a user’s goal into a structured course with chapters and lessons, generates learning assets (articles, YouTube picks, quizzes, coding projects), and includes a conversational tutor.

2) pennapps25 (Docker + code-server): a set of language-specific, browser-based VS Code environments. It doubles as the runtime workspace where CourseAI can materialize coding projects for hands-on practice and automated feedback.

The sections below explain the architecture, core models, data flow, and how the pieces interact.

## High-Level Architecture

- Web UI (Django templates) drives user interactions for: course generation, lesson navigation, quizzes, text responses, and project-based learning.
- AI/Infra services used by CourseAI:
  - Cerebras LLM: course/lesson planning, content generation, summarization, tutoring, grading/feedback heuristics.
  - Tavily: web search for fresh external sources and context.
  - Pinecone: vector search over curated content; used to enrich article generation.
  - YouTube Data API: identifies high-quality, time-bounded videos per lesson.
- Multi-language editor containers (code-server) provide isolated dev sandboxes. The Python workspace is directly integrated with CourseAI’s programming projects.
- SQLite stores canonical state: courses, lessons, quizzes, attempts, text answers, generated content, project files, and logs.

## Core Domains and Data Model

1) Course Generation (generation app)
	- CourseGeneration: root entity for a generated course with status tracking and the full JSON snapshot of the course structure.
	- GeneratedChapter: ordered chapters with names, descriptions, difficulty ratings.
	- GeneratedLesson: ordered lessons with type (vid, txt, mcq, int, art, ext, etc.), descriptive fields, and completion tracking.
	- LessonType: registry of available lesson types with IDs, names, and display labels.
	- GenerationLog: audit trail of generation steps, statuses, and payloads.

2) Learning Assets (generation app)
	- ArticleContent: long-form, AI-generated article for a lesson, optionally enriched by Pinecone/Tavily.
	- YouTubeVideo: selected video metadata for a lesson, chosen via YouTube API with AI-generated query.
	- ExternalArticles: link to an external article for reading.
	- MultipleChoiceQuiz / QuizAttempt: MCQ content and user attempt records with per-question correctness and aggregate score.
	- TextResponseQuestion / TextResponseSubmission: free-form Q&A with stored answers and grading metadata.

3) Projects and Files (courses app)
	- Project (courses.models): a programming assignment optionally tied 1:1 to a GeneratedLesson; stores grading method (AI review vs terminal matching), expected output (for matching), ownership and timestamps.
	- File: per-project file objects with relative paths and full content; supports reconstructing a workspace on disk.
	- A separate Project model also exists in generation.models for generated starter code bundles; the courses app persists and edits them as concrete files.

## Generation Pipeline (What Happens Under the Hood)

1) Course strategy
	- User provides a project goal + experience level.
	- `generation.views.chapter_list_create` prompts the Cerebras LLM to create up to 5 logically ordered chapters as pure JSON.
	- The system uses a primary and fallback Cerebras client. If parsing fails, it attempts robust JSON extraction.

2) Lesson planning
	- For each chapter, `generation.views.create_lesson` produces 5–8 lessons with varied lesson types (learning vs practice), goals, details, and creation guidelines.
	- Lessons are stored as `GeneratedLesson` rows with a `lesson_type` string and `lesson_type_id` from `LessonType`.

3) Asset creation per lesson
	- Articles: `ai_gen_article` distills main ideas, queries Pinecone (namespace "pennapps"), and writes a high-quality Markdown article via Cerebras. The output is saved in `ArticleContent`.
	- Videos: `youtube_utils.generate_youtube_query` asks the LLM to craft a targeted YouTube search query and constraints; `search_youtube` calls the YouTube API, fetches stats, and picks the top item by likes/views.
	- External reading: links saved in `ExternalArticles` where applicable.
	- Quizzes: `MultipleChoiceQuiz` stores questions/options/answers as JSON; attempts in `QuizAttempt` store user answers and results JSON plus score.
	- Text responses: `TextResponseQuestion` and `TextResponseSubmission` capture open-ended answers and grading.

4) Conversational tutoring
	- `home.views.chat_api` exposes a stateless-like chat API with session-based memory. It builds a system prompt (CourseAI Assistant persona), appends recent history (last ~20 messages), and calls Cerebras `chat.completions.create`.
	- `clear_chat` resets the session memory.

5) Logging and resilience
	- `GenerationLog` is used to track granular steps and outcomes.
	- JSON parsing throughout uses bracket-finding fallbacks to survive model drift or verbose responses.

## Hands-on Projects and the Editor Bridge

- The Python code-server workspace under `pennapps25/workspace-python/` is treated as the active sandbox.
- `courses.views.load_code_editor` clears that workspace (except `venv`) and reconstructs the project’s files from the DB into the filesystem, creating directories as needed.
- If a `project_id` is provided, all `File` rows for that project are materialized. Without one, a default Python file is created to ensure the workspace is usable.
- `save_project` accepts a JSON list of `{ relative_path, content }` and upserts them into the DB, supporting round-tripping from the editor into persistent storage.
- `get_workspace_files` walks the workspace directory, reads files, and returns them as JSON for saving.
- This bridge lets learners move seamlessly between generated instructions and real coding inside a browser editor, while keeping source-of-truth in the database.

## Routing Overview

- `home/`
  - `/` homepage template with chatbot UI
  - `/api/chat/` and `/api/chat/clear/` for chat operations

- `generation/`
  - `''` chatbot-initiated generation entry (plus `form/` legacy form)
  - `submit/`, `courses/`, `course/<id>/`, `lesson/<id>/(youtube|article|external|text)`
  - `quiz/<id>/` and `/submit/` for MCQs; `text/.../submit/` for free responses
  - `lesson/<id>/project/` and `final_project_feedback` for project interactions
  - `chat/*` endpoints to drive course generation via a conversational flow and check status

- `courses/`
  - `/` lists saved projects
  - `/editor/` optionally `/editor/<project_id>/` to materialize a project into the Python workspace
  - `/save_project/` and `/get_workspace_files/` to sync DB and workspace

## Services and Integrations

- Cerebras Cloud SDK: core LLM for planning, content, tutoring, and grading aids. Two keyed clients are supported for resilience.
- Pinecone: content retrieval; queries use lesson-reduced main ideas to pull relevant chunks (category and chunk_text fields).
- Tavily: live web search for current sources; filtered by score threshold.
- YouTube Data API: relevance-first search, then metric-based ranking (likes, views) to pick one best video per lesson.
- code-server containers (pennapps25): each language gets its own container, volume-mounting a workspace directory; Python’s workspace is the primary integration point for CourseAI projects.

## Data Flow at a Glance

1) User intent → Cerebras → structured course (CourseGeneration + chapters + lessons)
2) Each lesson → assets: Articles (Cerebras+Pinecone/Tavily), Videos (Cerebras+YouTube), Quizzes, Text prompts
3) Optional project lessons → DB-backed Project + File rows → projected into `workspace-python/` for editing
4) Learner interacts via web UI and browser-based editor → submissions and saves flow back into the DB
5) Chatbot overlays the experience with memory-aware assistance

## Security and Operational Notes

- All secrets are expected as environment variables (e.g., CEREBRAS_API_KEY, SECOND_CEREBRAS_API_KEY, PINECONE_API_KEY, PINECONE_HOST, TAVILY_API_KEY, YOUTUBE_API_KEY). Avoid committing them.
- SQLite is used for simplicity; for production, switch to a managed DB and configure static/media storage.
- Generation endpoints are designed to be tolerant of LLM formatting drift with JSON extraction fallbacks and logging.

## Further Reading

- Chatbot setup and behavior: `courseAI/CHATBOT_SETUP.md`
- Language environments and container makeup: `pennapps25/README.md`, `pennapps25/LANGUAGE_GUIDE.md`

