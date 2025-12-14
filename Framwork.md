Exploring the framework structure to list its components:


[7 tools called]


Reviewing key components in detail:


[5 tools called]


## Framework structure overview

```
nevo-backend-framework-main/
└── src/nevo_framework/
    ├── api/              # FastAPI server & endpoints
    ├── llm/              # AI/LLM components
    ├── config/           # Configuration management
    ├── helpers/          # Utility functions
    ├── testing/          # Test utilities
    └── playground/       # Experimental features
```

---

## 1. API module (`api/`)

FastAPI server and endpoints.

### Files:
- `api.py` — Main FastAPI application
- `api_helpers.py` — Helper functions for API
- `server_messages.py` — Message protocols
- `sessions.py` — Session management

### What it provides:

#### Endpoints:
```python
POST /login                    # Create session, get token
POST /receive_audio_blob       # Upload user audio
GET  /stop                     # Stop session
GET  /test                     # Health check
WS   /ws/audio/{session_id}    # WebSocket for audio streaming
WS   /ws/text/{session_id}     # WebSocket for text chat
```

#### Features:
- Authentication (JWT, password)
- Session management (multiple users)
- WebSocket handling (real-time streaming)
- CORS configuration
- Static file serving
- Error handling

---

## 2. LLM module (`llm/`)

AI/LLM components.

### Files:
- `agents.py` — Base agent classes
- `agent_orchestrator.py` — Orchestrator base class
- `dialog_manager.py` — Conversation management
- `llm_tools.py` — LLM utilities
- `openai_realtime.py` — Real-time OpenAI integration
- `stream_watching.py` — Stream monitoring

### What it provides:

#### Base classes:

1. `VoiceAgent` — Voice-enabled AI agent
   ```python
   class VoiceAgent:
       - Handles audio streaming
       - Manages conversation history
       - Supports function calling
       - Real-time audio generation
   ```

2. `StructuredOutputAgent` — Structured data extraction
   ```python
   class StructuredOutputAgent:
       - Extracts structured data from text
       - Returns Pydantic models
       - Type-safe responses
   ```

3. `GeneralAgentAsync` — Simple async agent
   ```python
   class GeneralAgentAsync:
       - Basic text-based agent
       - Async operations
       - Simple prompt/response
   ```

4. `AbstractAgentOrchestrator` — Orchestrator base
   ```python
   class AbstractAgentOrchestrator:
       - Manages multiple agents
       - Routes conversations
       - Handles agent switching
   ```

#### Utilities:

- `transcribe_recording()` — Speech-to-text (Whisper)
- `rewrite_query()` — Query improvement for RAG
- `trim_prompt()` — Prompt formatting
- `maybe_get()` — Type-safe message parsing

---

## 3. Config module (`config/`)

Configuration management.

### Files:
- `master_config.py` — Main configuration
- `audio_config.py` — Audio settings
- `prompts.json` — Default prompts

### What it provides:

#### MasterConfig:
```python
class MasterConfig:
    - orchestrator_class        # Which orchestrator to use
    - ai_speaks_first           # AI greets first?
    - llm_call_timeout         # Response timeout
    - voice_timing_coefficient # Audio/image sync
    - language_model_config    # OpenAI/Azure settings
    - session_cleanup_interval # Session management
    - recording_file_dir       # Where to save audio
```

#### AudioConfig:
```python
class AudioConfig:
    - voice: str = "onyx"
    - channels: int = 1
    - sample_width: int = 2
    - sample_rate: int = 24000
```

---

## 4. Helpers module (`helpers/`)

Utility functions.

### Files:
- `instantiation.py` — Dynamic class instantiation
- `logging_helpers.py` — Logging utilities
- `file_tools.py` — File operations
- `file_hashing.py` — File hashing
- `convert_specs.py` — Data conversion

### What it provides:

- `create_instance_from_string()` — Create classes from config
- Logging helpers for AI responses
- File utilities
- Data conversion tools

---

## 5. Testing module (`testing/`)

Test utilities.

### Files:
- `testing_bot.py` — Test bot implementation
- `testing_client.py` — Test client
- `test_helpers.py` — Test utilities
- `simple_agents.py` — Simple test agents

### What it provides:

- Headless testing (no frontend)
- Test agents for development
- Testing utilities
- Mock implementations

---

## 6. Playground module (`playground/`)

Experimental features.

### Files:
- `datamodel.py` — Experimental data models
- `prompt_repo.py` — Prompt repository

---

## Complete feature list

### Infrastructure:
- FastAPI server
- WebSocket support (audio & text)
- Session management
- Authentication (JWT)
- CORS handling
- Static file serving
- Error handling

### AI/LLM:
- VoiceAgent (voice-enabled)
- StructuredOutputAgent (data extraction)
- GeneralAgentAsync (simple agent)
- AbstractAgentOrchestrator (multi-agent)
- Dialog management
- Conversation history
- Function calling support

### Audio:
- Speech-to-text (Whisper)
- Text-to-speech (GPT-4o-audio)
- Real-time audio streaming
- Audio chunking
- Audio file handling
- Voice timing calculations

### Communication:
- Server-to-frontend messages
- Frontend-to-backend messages
- Web element messages
- Status messages
- Text chunk messages
- End-of-stream signals

### Utilities:
- Query rewriting (for RAG)
- Prompt formatting
- Type-safe message parsing
- Dynamic class instantiation
- Logging helpers
- File utilities

### Configuration:
- Master config (JSON)
- Audio config
- Model selection (OpenAI/Azure)
- Timeout settings
- Session settings
- Debug flags

---

## What you get vs what you build

### Framework provides (you don't build):
- WebSocket server
- Audio streaming
- Session management
- Authentication
- STT/TTS integration
- Dialog management
- Agent base classes
- Message protocols
- Error handling
- Configuration system

### You build (business logic):
- Orchestrator (conversation flow)
- Agents (specialized roles)
- RAG documents (knowledge base)
- System prompts (personality)
- Business rules (when to switch agents)
- Frontend UI (optional)

---

## Summary

The framework includes:
- API server (FastAPI, WebSocket, endpoints)
- AI components (agents, orchestrator, dialog management)
- Audio handling (STT, TTS, streaming)
- Session management (auth, state, cleanup)
- Configuration (JSON-based, flexible)
- Utilities (helpers, testing, logging)
- Communication protocols (messages, WebSocket)

You focus on:
- Business logic (orchestrator)
- Specialized agents
- Product knowledge (RAG)
- Conversation flow

The framework handles the infrastructure; you build the intelligence.




Yes, this framework is useful for building Gen-AI chatbots/assistants. Here's why:

## What makes this framework useful

### 1. Handles complex infrastructure
Building from scratch requires:
- WebSocket real-time audio streaming
- Speech-to-text (Whisper) integration
- Text-to-speech (GPT-4o-audio) streaming
- Session management and authentication
- Audio chunking and buffering
- CORS and security

This framework provides all of this, so you can focus on business logic.

### 2. Clean separation of concerns

```
Framework (Infrastructure)
    ↓
Your Orchestrator (Business Logic)
    ↓
Your Agents (Specialized Roles)
    ↓
Your RAG Documents (Knowledge)
```

You customize the orchestrator and agents; the framework handles the rest.

### 3. Production-ready features

What you get out of the box:
- Session management (multiple users, cleanup)
- Authentication (JWT, password protection)
- Error handling and timeouts
- Logging and debugging
- Audio streaming optimization
- WebSocket connection management

### 4. Flexible agent system

You can create specialized agents:
```python
# Different agents for different purposes
UserProfileAgent → Collects customer info
ProductDetailAgent → Explains products
BookingAgent → Handles appointments
SupportAgent → Troubleshooting
```

Each agent can have:
- Custom system prompts
- RAG knowledge bases
- Function calling
- Different LLM models

### 5. RAG integration built-in

The framework makes RAG straightforward:
```python
# Easy to add your own knowledge
self.vectordb = VectorDB("documents/my_product_knowledge.json")
results = self.vectordb.search_with_query(user_query)
# Use results in agent's system prompt
```

---

## Comparison: with framework vs without

### Building from scratch (without framework)

Time estimate: 2-4 months

What you'd need to build:
1. WebSocket server (FastAPI + WebSockets)
2. Audio streaming (chunking, buffering, synchronization)
3. STT integration (Whisper API calls, error handling)
4. TTS streaming (GPT-4o-audio, real-time chunks)
5. Session management (state, cleanup, persistence)
6. Authentication (JWT, cookies, security)
7. Dialog management (conversation history)
8. Agent orchestration (routing, state management)
9. Error handling (timeouts, retries, fallbacks)
10. Testing and debugging tools

Challenges:
- Audio synchronization issues
- WebSocket connection management
- Session state management
- Error handling edge cases
- Performance optimization

### Using this framework

Time estimate: 1-2 weeks

What you build:
1. Orchestrator (conversation flow logic)
2. Agents (specialized AI roles)
3. RAG documents (your product knowledge)
4. Frontend UI (optional customization)

What you get:
- All infrastructure already built
- Production-ready code
- Best practices implemented
- Tested and optimized

---

## When this framework is a good fit

### Good for:
1. Voice-first chatbots
   - Customer service
   - Sales assistants
   - Product advisors
   - Support bots

2. Multi-agent systems
   - Different agents for different tasks
   - Complex conversation flows
   - Specialized knowledge bases

3. RAG-powered assistants
   - Product catalogs
   - Documentation
   - Knowledge bases
   - Training materials

4. Custom business logic
   - Sales processes
   - Booking systems
   - Data collection
   - CRM integration

### May not be ideal for:
1. Simple text-only chatbots
   - Overkill if you don't need voice
   - Use simpler frameworks (LangChain, etc.)

2. Very simple use cases
   - Single-purpose bots
   - No complex routing needed

3. Non-Python backends
   - Framework is Python-based
   - Would need porting

---

## What makes this framework special

### 1. Voice-first design
Most frameworks focus on text. This one is built for real-time voice:
- Audio streaming
- Voice timing calculations
- Natural conversation flow

### 2. Agent orchestration pattern
Clean pattern for multi-agent systems:
```python
# Easy to add new agents
class MyNewAgent(VoiceAgent):
    def __init__(self):
        # Your custom logic
        pass

# Easy to route
if user_asks_about_X:
    self.speaking_agent = MyNewAgent()
```

### 3. Production-ready
Not a prototype—includes:
- Error handling
- Timeouts
- Session cleanup
- Security
- Logging

### 4. Flexible configuration
Easy to customize:
```json
{
  "orchestrator_class": "your.orchestrator.YourOrchestrator",
  "ai_speaks_first": true,
  "llm_call_timeout": 30.0
}
```

---

## Real-world use cases

### 1. E-commerce sales assistant
```python
# Your orchestrator
class SalesOrchestrator(AbstractAgentOrchestrator):
    def __init__(self):
        self.greeting_agent = GreetingAgent()
        self.product_agent = ProductAgent()  # Uses RAG with product catalog
        self.checkout_agent = CheckoutAgent()
```

### 2. Technical support bot
```python
class SupportOrchestrator(AbstractAgentOrchestrator):
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.troubleshooting_agent = TroubleshootingAgent()  # Uses RAG with docs
        self.escalation_agent = EscalationAgent()
```

### 3. Appointment booking
```python
class BookingOrchestrator(AbstractAgentOrchestrator):
    def __init__(self):
        self.availability_agent = AvailabilityAgent()
        self.booking_agent = BookingAgent()  # Integrates with calendar API
```

---

## My assessment

### Strengths
1. Saves significant development time (months → weeks)
2. Production-ready infrastructure
3. Clean architecture (separation of concerns)
4. Flexible (easy to customize)
5. Voice-optimized (real-time audio)
6. Multi-agent support (complex flows)

### Considerations
1. Learning curve (understand orchestrator pattern)
2. Python-only (if you need other languages)
3. Framework dependency (updates/maintenance)
4. Overkill for simple text bots

### Verdict
Highly useful if you need:
- Voice-enabled chatbots
- Multi-agent systems
- RAG-powered assistants
- Production-ready infrastructure
- Custom business logic

Less ideal if you need:
- Simple text-only bots
- Non-Python backends
- Very simple use cases

---

## Bottom line

This framework is valuable for building production Gen-AI chatbots/assistants. It handles the hard infrastructure (voice, WebSockets, sessions) so you can focus on your business logic (orchestrator, agents, RAG).

It's like using React for web apps—you could build from scratch, but the framework accelerates development and provides proven patterns.

For your use case (sales assistant that can adapt to different products like AC, phones, etc.), this framework fits well because:
- You can swap orchestrators for different products
- Each product can have its own agents and RAG docs
- Voice-first is good for sales interactions
- Production-ready for real customers

Recommendation: use it. It will save months of development time and let you focus on what makes your chatbot unique.


Comparing the shop version (`Nevo-Framwork-chat-bot`) with the pitch version. Exploring the shop version:


[6 tools called]


Exploring more details to compare both versions:


[5 tools called]


## Comparison: Shop version vs Pitch version

---

## Feature comparison

| Feature | Shop Version<br/>(Nevo-Framwork-chat-bot) | Pitch Version<br/>(nevo-audi-pitch-backend-main) |
|---------|-------------------------------------------|---------------------------------------------------|
| **Database** | ✅ PostgreSQL (sessions + conversations) | ❌ In-memory only |
| **Session Persistence** | ✅ Persistent across restarts | ❌ Lost on restart |
| **Conversation History** | ✅ Stored in database | ❌ In-memory only |
| **CRM Integration** | ❌ None | ✅ Salesforce |
| **Deployment** | ✅ Docker + Terraform + Azure | ❌ Local dev only |
| **Production Ready** | ✅ Yes | ⚠️ Demo-focused |
| **Database Migrations** | ✅ Alembic | ❌ None |
| **Vehicle Search** | ✅ Structured search with filters | ❌ Profile-based recommendations |
| **Vehicle Comparison** | ✅ Side-by-side comparison | ❌ No comparison |
| **Product Specs** | ✅ Structured data retrieval | ⚠️ RAG-based |
| **User Profile Collection** | ❌ No | ✅ Yes |
| **Test Drive Booking** | ❌ No | ✅ Yes |
| **Image Walkaround** | ❌ No | ✅ Yes (car tour) |
| **RAG Documents** | ✅ Directory-based (.md files) | ✅ JSON-based |
| **Orchestrator** | `AudiOrchestrator` (search/comparison) | `AudiAgentOrchestrator` (profile → recommendation) |
| **Frontend** | Material-UI (e-commerce) | Tailwind + 3D (showroom) |
| **Infrastructure** | ✅ Complete (Azure, Terraform) | ❌ None |
| **Managed Identity Auth** | ✅ Azure Managed Identity | ❌ API keys only |
| **Key Vault Integration** | ✅ Yes | ❌ No |

---

## Detailed breakdown

### 1. Database & persistence

**Shop version:**
```python
# PostgreSQL database with 2 tables:
- sessions (id, created_at, last_activity, modality)
- conversations (id, session_id, role, content, timestamp)

✅ Sessions persist across restarts
✅ Conversation history saved
✅ Can query past conversations
```

**Pitch version:**
```python
# In-memory only
❌ Sessions lost on restart
❌ No conversation history
❌ No database queries
```

---

### 2. Features

**Shop version:**
- ✅ Vehicle search (structured, filterable)
- ✅ Vehicle comparison (side-by-side)
- ✅ Product detail pages
- ✅ Structured product specs
- ✅ RAG for marketing copy
- ❌ No user profile collection
- ❌ No test drive booking
- ❌ No image walkaround

**Pitch version:**
- ✅ User profile collection
- ✅ Personalized recommendations
- ✅ Test drive booking
- ✅ Image walkaround tours
- ✅ Safety features explanation
- ✅ Salesforce integration
- ❌ No vehicle search
- ❌ No vehicle comparison

---

### 3. Infrastructure & deployment

**Shop version:**
```
✅ Docker containers
✅ Terraform for Azure
✅ Azure App Service
✅ PostgreSQL Flexible Server
✅ Key Vault integration
✅ Managed Identity auth
✅ Production-ready deployment
✅ CI/CD ready
```

**Pitch version:**
```
❌ No Docker
❌ No Terraform
❌ No Azure deployment
❌ No database
❌ Local development only
❌ Manual setup required
```

---

### 4. Orchestrator & agents

**Shop version:**
```python
# AudiOrchestrator
- IntroductionVoiceAgent
- VehicleSearchVoiceAgent
- VehicleComparisonVoiceAgent
- ProductDisplayVoiceAgent
- GapFillingVoiceAgent
- GeneralQueryVoiceAgent
- RAGRetriever (marketing copy)
```

**Pitch version:**
```python
# AudiAgentOrchestrator
- UserProfileVoiceAgent
- CarRecommendationAgent
- CarDetailAgent
- SafetyFeatureAgent
- TestDriveVoiceAgent
- CarTourAgent
- ImageCommentaryAgent
```

---

### 5. RAG implementation

**Shop version:**
```
Documents: documents/generated_vehicle_copy/ (directory of .md files)
Format: Plain text/markdown
Embedding: text-embedding-ada-002
Loading: Directory-based, lazy initialization
```

**Pitch version:**
```
Documents: documents/audi_documents/*.json (structured JSON)
Format: KnowledgeBase JSON with metadata
Embedding: text-embedding-3-small
Loading: JSON-based, car model filtering
```

---

### 6. Frontend

**Shop version:**
- Material-UI components
- Product catalog UI
- Search results grid
- Comparison tables
- Product detail pages
- Traditional e-commerce layout

**Pitch version:**
- Tailwind CSS
- 3D showroom (Three.js)
- Dark theme
- Voice-first interaction
- Immersive demo experience

---

## Recommendation: which to use?

### Use Shop version if you need:
1. ✅ Production deployment (Docker, Azure, Terraform)
2. ✅ Database persistence (PostgreSQL)
3. ✅ Vehicle search and comparison
4. ✅ Structured product data
5. ✅ E-commerce features
6. ✅ Scalability and reliability
7. ✅ Managed Identity authentication
8. ✅ Conversation history

### Use Pitch version if you need:
1. ✅ User profile collection
2. ✅ Personalized recommendations
3. ✅ Test drive booking
4. ✅ Salesforce CRM integration
5. ✅ Image walkaround tours
6. ✅ Sales pitch/demo focus
7. ✅ Simpler local development

---

## Best option: Shop version (for all features)

### Why Shop version is better:
1. ✅ Production-ready (deployment, infrastructure)
2. ✅ Database persistence (sessions, conversations)
3. ✅ More features (search, comparison, product specs)
4. ✅ Better architecture (Docker, Terraform, Azure)
5. ✅ Scalable (PostgreSQL, managed services)
6. ✅ Secure (Managed Identity, Key Vault)

### What you can add to Shop version:
You can add Pitch features to Shop version:
```python
# Add to Shop version:
1. User profile collection (copy from Pitch)
2. Test drive booking (copy from Pitch)
3. Salesforce integration (copy from Pitch)
4. Image walkaround (copy from Pitch)

# Result: Shop version + Pitch features = BEST OF BOTH!
```

---

## Final answer

Use `Nevo-Framwork-chat-bot/nevo-audi-shop-backend-main` (Shop version) because:
- ✅ Production-ready infrastructure
- ✅ Database persistence
- ✅ More features (search, comparison)
- ✅ Better deployment setup
- ✅ Can add Pitch features to it

Then add Pitch features:
- User profile collection
- Test drive booking
- Salesforce integration
- Image walkaround

Result: Shop version foundation + Pitch features = complete solution.

---

## Quick decision guide

```
Need production deployment? → Shop version ✅
Need database persistence? → Shop version ✅
Need vehicle search/comparison? → Shop version ✅
Need user profiles/test drives? → Add to Shop version ✅
Need Salesforce? → Add to Shop version ✅

Want everything? → Shop version + add Pitch features ✅
```

Bottom line: Start with Shop version, then add Pitch features. You get the best of both.


Clarifying what's reusable (framework) vs what needs customization (business logic):


[5 tools called]


Clarifying what's reusable vs what needs to change:


[3 tools called]


## Architecture breakdown: what's reusable vs what to change

---

## Framework (reusable — no changes)

**Location:** `nevo-backend-framework-main/src/nevo_framework/`

**What it provides:**
- Voice infrastructure: WebSocket, audio streaming, STT/TTS
- API server: FastAPI, authentication, session management
- Base classes: `AbstractAgentOrchestrator`, `VoiceAgent`, `StructuredOutputAgent`
- LLM clients: OpenAI/Azure OpenAI integration
- Dialog management: Conversation tracking, state management
- Utilities: RAG helpers, logging, file tools

**No product-specific code** — works for cars, ACs, phones, etc.

---

## Backend business logic (change for new product)

**Location:** `nevo-audi-pitch-backend-main/src/llm/`

### What to change for AC/Phone:

#### 1. Orchestrator (`audi_orchestrator.py` → `product_orchestrator.py`)
```python
# CURRENT (Audi):
class AudiAgentOrchestrator(AbstractAgentOrchestrator):
    def __init__(self):
        self.speaking_agent = user_profile.UserProfileVoiceAgent()
        self.car_detail_agent = recommendation.CarDetailAgent()
        self.safety_feature_agent = recommendation.SafetyFeatureAgent()
        # ... car-specific logic

# CHANGE TO (AC/Phone):
class ProductOrchestrator(AbstractAgentOrchestrator):
    def __init__(self):
        self.speaking_agent = user_profile.UserProfileVoiceAgent()
        self.product_detail_agent = recommendation.ProductDetailAgent()  # Changed
        self.feature_agent = recommendation.FeatureAgent()  # Changed
        # ... product-specific logic
```

#### 2. Agents (create new agents for your product)
```python
# CURRENT: CarDetailAgent, SafetyFeatureAgent, TestDriveAgent
# CHANGE TO: ProductDetailAgent, FeatureAgent, BookingAgent

# Example for AC:
class ACDetailAgent(VoiceAgent):
    def __init__(self):
        # Load AC knowledge base instead of car knowledge
        self.vectordb = VectorDB("documents/ac_documents/ac_knowledge.json")
        
    async def rag_lookup(self, dialog, ac_model="Split AC"):
        # Search AC-specific documents
        results = self.vectordb.search_with_query(query, product_model=ac_model)
```

#### 3. RAG documents (replace with your product docs)
```
# CURRENT:
documents/audi_documents/knowledge_base_2025-02-24_11-28-19 LARGE_FIXED.json

# CHANGE TO:
documents/ac_documents/ac_knowledge_base.json
# OR
documents/phone_documents/phone_knowledge_base.json
```

#### 4. Constants (`constants.py`)
```python
# CURRENT:
AUDI_MODEL_DATA_FILE = "documents/audi_documents/..."
AUDI_MODEL_VECTOR_INDEX_PATH = "documents/audi_documents/..."

# CHANGE TO:
PRODUCT_DATA_FILE = "documents/ac_documents/ac_knowledge.json"
PRODUCT_VECTOR_INDEX_PATH = "documents/ac_documents/ac_index.pkl"
```

#### 5. Config (`config/master_config.json`)
```json
{
  "orchestrator_class": "llm.audi_orchestrator.AudiAgentOrchestrator"
  // CHANGE TO:
  "orchestrator_class": "llm.product_orchestrator.ProductOrchestrator"
}
```

---

## Frontend (change for new product)

**Location:** `audi-nevo-frontend-main/src/`

### What to change:

#### 1. UI components
```typescript
// CURRENT: CarShowroom.tsx
// CHANGE TO: ProductShowroom.tsx or ACShowroom.tsx

// Change:
- Car images → Product images
- Car colors → Product variants (size, color, model)
- Car models → Product models
```

#### 2. Product types
```typescript
// CURRENT: ICar interface
interface ICar {
  id: number;
  colorOptions: string[];
  image: string;
  colorName: string;
  price: number;
}

// CHANGE TO: IProduct interface
interface IProduct {
  id: number;
  variants: string[];  // Instead of colorOptions
  image: string;
  modelName: string;  // Instead of colorName
  price: number;
  specifications?: string[];  // For AC: cooling capacity, energy rating, etc.
}
```

#### 3. Images/assets
```
// CURRENT:
public/audi/car_views/...

// CHANGE TO:
public/ac/products/...
// OR
public/phone/products/...
```

---

## Step-by-step: adapt for AC/Phone

### Step 1: Backend — create new orchestrator
```python
# Create: src/llm/product_orchestrator.py
class ProductOrchestrator(AbstractAgentOrchestrator):
    def __init__(self, output_queue, chat_modality):
        super().__init__(output_queue, chat_modality)
        # Replace car agents with product agents
        self.product_detail_agent = ProductDetailAgent()
        self.feature_agent = FeatureAgent()
        # ... your product logic
```

### Step 2: Backend — create product agents
```python
# Create: src/llm/product_agents.py
class ProductDetailAgent(VoiceAgent):
    def __init__(self):
        # Load YOUR product knowledge base
        self.vectordb = VectorDB("documents/ac_documents/ac_knowledge.json")
        super().__init__(name="ProductDetailAgent", ...)
```

### Step 3: Backend — add product documents
```bash
# Create your RAG documents
documents/ac_documents/
  ├── ac_knowledge.json          # Product specs, features
  ├── ac_index.pkl              # Pre-computed embeddings
  └── ac_features.json          # Feature descriptions
```

### Step 4: Backend — update config
```json
// config/master_config.json
{
  "orchestrator_class": "llm.product_orchestrator.ProductOrchestrator"
}
```

### Step 5: Frontend — update UI
```typescript
// Change CarShowroom → ProductShowroom
// Update product display logic
// Change image paths
// Update product-specific UI elements
```

---

## What stays the same (framework)

- Voice system: WebSocket, audio streaming, STT/TTS
- API endpoints: `/login`, `/ws/audio/{session_id}`, `/receive_audio_blob`
- Session management: Authentication, JWT, session tracking
- Base agent classes: `VoiceAgent`, `StructuredOutputAgent`
- LLM integration: OpenAI/Azure OpenAI clients
- Dialog management: Conversation tracking

---

## Summary: change matrix

| Component | Framework | Backend | Frontend |
|-----------|-----------|---------|----------|
| Voice/Audio | ✅ Reusable | ❌ N/A | ❌ N/A |
| WebSocket | ✅ Reusable | ❌ N/A | ❌ N/A |
| API Server | ✅ Reusable | ❌ N/A | ❌ N/A |
| Orchestrator | ✅ Base class | ❌ Rewrite | ❌ N/A |
| Agents | ✅ Base classes | ❌ Create new | ❌ N/A |
| RAG Documents | ✅ VectorDB class | ❌ Replace docs | ❌ N/A |
| Product Logic | ❌ N/A | ❌ Rewrite | ❌ N/A |
| UI Components | ❌ N/A | ❌ N/A | ❌ Rewrite |
| Product Images | ❌ N/A | ❌ N/A | ❌ Replace |

---

## Example: AC product

**Backend changes:**
1. `AudiAgentOrchestrator` → `ACOrchestrator`
2. `CarDetailAgent` → `ACDetailAgent`
3. Documents: `documents/ac_documents/ac_specs.json`
4. Config: `"orchestrator_class": "llm.ac_orchestrator.ACOrchestrator"`

**Frontend changes:**
1. `CarShowroom` → `ACShowroom`
2. Images: `public/ac/products/...`
3. UI: Show AC specs (BTU, energy rating, size) instead of car specs

**Framework:**
- No changes needed

---

## Quick answer

- Framework: Reusable infrastructure (voice, API, base classes)
- Backend: Business logic (orchestrator, agents, RAG docs) — change for new product
- Frontend: UI (components, images, product display) — change for new product

To adapt for AC/Phone:
1. Create new orchestrator and agents
2. Replace RAG documents with product docs
3. Update frontend UI and images
4. Framework stays the same

The framework is product-agnostic; the backend and frontend contain the product-specific logic.

Explaining what an Orchestrator is and the framework configuration from a sales agent perspective:


[4 tools called]


## What is an Orchestrator?

The Orchestrator is the central controller that manages the sales conversation flow.

### Simple analogy

Think of it like a sales manager:
- Framework = Office infrastructure (phones, computers, building)
- Orchestrator = Sales manager (decides which salesperson handles the customer)
- Agents = Salespeople (specialized roles: greeting, product expert, closer)

### How it works

```
User speaks
    ↓
Framework receives audio → transcribes
    ↓
Framework calls: orchestrator.dialog_step()
    ↓
Orchestrator decides: "Which agent should respond?"
    ↓
Orchestrator calls: agent.dialog_step()
    ↓
Agent responds (using RAG, knowledge base)
    ↓
Framework streams response back to user
```

### In your code

**Framework provides:**
```python
# AbstractAgentOrchestrator (base class)
class AbstractAgentOrchestrator:
    def __init__(self, output_queue, chat_modality):
        # Framework sets up voice/audio infrastructure
        self._output_queue = output_queue  # For sending audio
        self._chat_modality = chat_modality  # "audio" or "text"
    
    @abc.abstractmethod
    async def dialog_step(self, dialog, web_element_message):
        # YOU implement this - decides which agent to use
        raise NotImplementedError
```

**Your backend implements:**
```python
# AudiAgentOrchestrator (your business logic)
class AudiAgentOrchestrator(AbstractAgentOrchestrator):
    def __init__(self):
        # Create specialized agents
        self.user_profile_agent = UserProfileVoiceAgent()  # Collects customer info
        self.car_detail_agent = CarDetailAgent()          # Knows about cars
        self.safety_feature_agent = SafetyFeatureAgent()  # Knows safety features
        self.test_drive_agent = TestDriveVoiceAgent()     # Books test drives
    
    async def dialog_step(self, dialog, web_element_message):
        # YOUR LOGIC: Decide which agent to use based on conversation
        if user_profile_collected:
            self.speaking_agent = self.car_detail_agent  # Switch to car expert
        elif user_asks_about_safety:
            self.speaking_agent = self.safety_feature_agent  # Switch to safety expert
        # ... etc
        
        return await self.speaking_agent.dialog_step(dialog)
```

---

## Framework configuration (sales agent perspective)

The framework configures the infrastructure; your orchestrator defines the sales flow.

### Configuration in `master_config.json`

```json
{
  "orchestrator_class": "llm.audi_orchestrator.AudiAgentOrchestrator",
  "ai_speaks_first": true,
  "llm_call_timeout": 30.0,
  "voice_timing_coefficient": 0.0678655,
  "voice_timing_offset": 1.2,
  "context_by_phase_cutoff": true
}
```

### What each setting does

#### 1. `orchestrator_class`
```json
"orchestrator_class": "llm.audi_orchestrator.AudiAgentOrchestrator"
```
- Purpose: Tells framework which orchestrator to use
- Sales perspective: Which sales manager/flow to use
- Change for AC/Phone: `"llm.ac_orchestrator.ACOrchestrator"`

#### 2. `ai_speaks_first`
```json
"ai_speaks_first": true
```
- Purpose: Whether AI greets the customer first
- Sales perspective: Proactive greeting vs waiting
- Example: `true` = "Hello! How can I help you today?"

#### 3. `llm_call_timeout`
```json
"llm_call_timeout": 30.0
```
- Purpose: Max seconds to wait for AI response
- Sales perspective: Prevents long pauses

#### 4. `voice_timing_coefficient` & `voice_timing_offset`
```json
"voice_timing_coefficient": 0.0678655,
"voice_timing_offset": 1.2
```
- Purpose: Calculates when to show images during speech
- Sales perspective: Syncs product images with speech

#### 5. `context_by_phase_cutoff`
```json
"context_by_phase_cutoff": true
```
- Purpose: Clears old conversation when moving to a new phase
- Sales perspective: Focuses on current topic (e.g., test drive booking)

---

## Framework configuration flow

### Step 1: Framework reads config
```python
# In master_config.py
CONFIG = _load_config_from_json("config/master_config.json")
# Reads: orchestrator_class, ai_speaks_first, etc.
```

### Step 2: Framework creates orchestrator
```python
# In dialog_manager.py
def _set_orchestrator_from_config(self):
    # Framework finds your orchestrator class
    orchestrator = create_instance_from_string(
        CONFIG.orchestrator_class,  # "llm.audi_orchestrator.AudiAgentOrchestrator"
        output_queue=self._output_queue,
        chat_modality=chat_modality
    )
    # Creates: AudiAgentOrchestrator instance
```

### Step 3: Framework calls your orchestrator
```python
# When user speaks:
async def dialog_step(self, recording_file_path):
    # Framework transcribes audio
    transcription = await transcribe(recording_file_path)
    
    # Framework calls YOUR orchestrator
    response = await self._agent_orchestrator.dialog_step(
        dialog=conversation_history,
        web_element_message=None
    )
    
    # Framework streams response back
    await stream_response(response)
```

---

## Sales agent perspective: what's configured

### Framework configures (infrastructure)

| Setting | Purpose | Sales Impact |
|---------|---------|--------------|
| `ai_speaks_first` | AI greets first | Proactive vs reactive |
| `llm_call_timeout` | Response timeout | Prevents long waits |
| `voice_timing_*` | Image timing | Syncs visuals with speech |
| `context_by_phase_cutoff` | Context management | Focuses on current topic |
| `timeout_session_activity` | Session cleanup | Manages idle customers |

### Your orchestrator configures (sales flow)

| Component | Purpose | Sales Impact |
|-----------|---------|--------------|
| Agent selection | Which agent responds | Right expertise at the right time |
| RAG documents | Product knowledge | What the agent knows |
| Conversation flow | State transitions | Sales process steps |
| System prompts | Agent personality | How the agent speaks |

---

## Example: sales conversation flow

```
1. Customer arrives
   Framework: ai_speaks_first=true → AI greets first
   Orchestrator: Uses UserProfileVoiceAgent
   Result: "Hello! I'm here to help you find the perfect car. What brings you in today?"

2. Customer describes needs
   Orchestrator: UserProfileVoiceAgent collects info
   Result: "I need a family car for city driving"

3. Profile collected
   Orchestrator: Switches to CarRecommendationAgent
   RAG: Searches car knowledge base
   Result: "Based on your needs, I recommend the Audi Q3..."

4. Customer asks about safety
   Orchestrator: Switches to SafetyFeatureAgent
   RAG: Searches safety features knowledge base
   Result: "The Q3 has advanced safety features like..."

5. Customer wants test drive
   Orchestrator: Switches to TestDriveVoiceAgent
   Result: "Great! When would you like to schedule?"

6. Test drive booked
   Orchestrator: Writes to Salesforce (if configured)
   Result: Lead saved for sales team
```

---

## Summary

### Orchestrator
- Central controller for the sales conversation
- Decides which agent handles each step
- Manages conversation state and flow
- You implement it; framework calls it

### Framework configuration (sales perspective)
- Infrastructure settings: timeouts, voice timing, session management
- Orchestrator selection: which orchestrator to use
- No product-specific logic: framework is product-agnostic

### Your orchestrator (sales logic)
- Agent selection: which agent responds
- RAG integration: product knowledge
- Conversation flow: sales process steps
- Business rules: when to switch agents

The framework provides the infrastructure; your orchestrator defines the sales strategy.

Checking how the orchestrator controls the conversation flow, including the first message:


[4 tools called]


Tracing how the orchestrator controls the conversation flow, including the first message:


[2 tools called]


Yes. The orchestrator decides the conversation flow, including which agent speaks first. The first words come from that agent's system prompt.

## How the orchestrator controls the first message

### Step 1: Framework checks config
```python
# In api.py (line 277)
if ai_speaks_first:  # From config: "ai_speaks_first": true
    await handle_dialog_step(
        websocket=websocket,
        recording_file_path=None,  # No user input yet!
        web_element_message=None,
        session_state=session_state,
    )
```

### Step 2: Framework calls orchestrator with empty dialog
```python
# In dialog_manager.py (line 104)
response = await self._agent_orchestrator.dialog_step(
    dialog=[],  # Empty dialog - no conversation yet!
    web_element_message=None
)
```

### Step 3: Orchestrator decides which agent speaks first
```python
# In audi_orchestrator.py (line 40-47)
class AudiAgentOrchestrator(AbstractAgentOrchestrator):
    def __init__(self, output_queue, chat_modality):
        super().__init__(output_queue, chat_modality)
        
        # ORCHESTRATOR DECIDES: UserProfileVoiceAgent speaks first
        self.speaking_agent = user_profile.UserProfileVoiceAgent()
        # This agent will handle the first message
```

### Step 4: Orchestrator routes to the correct agent
```python
# In audi_orchestrator.py (line 446-465)
async def dialog_step(self, dialog, web_element_message):
    # ORCHESTRATOR DECIDES: Which agent handles this step
    
    if isinstance(self.speaking_agent, user_profile.UserProfileVoiceAgent):
        # Route to user profile collection
        response = await self.chat_step__user_profile_state(dialog=dialog)
    
    elif isinstance(self.speaking_agent, recommendation.CarRecommendationAgent):
        # Route to car recommendation
        response = await self.chat_step__recommender_and_details_state(...)
    
    # ... etc
```

### Step 5: Agent's system prompt defines the first words
```python
# In user_profile_agent.py (line 28-54)
class UserProfileVoiceAgent(VoiceAgent):
    def __init__(self):
        system_prompt = trim_prompt(
            f"""You are an expert car salesman named {data.ASSISTANT_NAME}. 
            You approach a customer in a friendly and chatty way...
            
            The first thing you do is introduce yourself and tell the customer 
            that you will ask a few questions to recommend the best car for them. 
            Let them know they can also load info from a previous conversation 
            if they share their email address. Then ask your first question.
            """
        )
        # This system prompt tells the AI what to say first!
```

---

## Complete flow: first message

```
1. User connects to WebSocket
   ↓
2. Framework checks: ai_speaks_first = true
   ↓
3. Framework calls: orchestrator.dialog_step(dialog=[])
   ↓
4. Orchestrator checks: Which agent is speaking_agent?
   → Answer: UserProfileVoiceAgent (set in __init__)
   ↓
5. Orchestrator calls: UserProfileVoiceAgent.dialog_step(dialog=[])
   ↓
6. Agent reads system prompt:
   "The first thing you do is introduce yourself..."
   ↓
7. Agent generates first message:
   "Hello! I'm [ASSISTANT_NAME]. I'll ask a few questions 
    to recommend the best car for you. What's your first name?"
   ↓
8. Framework streams response to user
```

---

## Orchestrator controls

### 1. Which agent speaks first
```python
# In __init__:
self.speaking_agent = user_profile.UserProfileVoiceAgent()  # ← YOU DECIDE
```

### 2. Conversation flow (when to switch agents)
```python
# In dialog_step:
if user_profile_collected:
    self.speaking_agent = recommendation.CarRecommendationAgent()  # ← YOU DECIDE
elif user_asks_about_safety:
    self.speaking_agent = recommendation.SafetyFeatureAgent()  # ← YOU DECIDE
```

### 3. What each agent does (via system prompts)
```python
# Each agent has a system prompt that defines its behavior
UserProfileVoiceAgent → Collects customer info
CarRecommendationAgent → Recommends cars
SafetyFeatureAgent → Explains safety features
```

---

## Example: changing the first message

### Option 1: Change which agent speaks first
```python
# In audi_orchestrator.py __init__:
# OLD:
self.speaking_agent = user_profile.UserProfileVoiceAgent()

# NEW (if you want car expert to speak first):
self.speaking_agent = recommendation.CarDetailAgent()
```

### Option 2: Change the agent's system prompt
```python
# In user_profile_agent.py:
system_prompt = trim_prompt(
    """You are a friendly sales assistant.
    
    The first thing you do is say: 
    'Welcome to our showroom! How can I help you today?'
    """
)
```

### Option 3: Change config (framework level)
```json
// config/master_config.json
{
  "ai_speaks_first": false  // User speaks first instead
}
```

---

## Summary

- Orchestrator decides which agent speaks first (set in `__init__`).
- Orchestrator controls the conversation flow (switches agents in `dialog_step`).
- Agent's system prompt defines the actual first words.
- Framework handles the infrastructure (WebSocket, audio, calling the orchestrator).

The orchestrator is the decision-maker; the agent's system prompt provides the words.