# Forge

## Vision Document & Project Context

---

# What is Forge?

Forge is an **open-source AI Agent Runtime and Engineering Platform** built from first principles.

Forge is **not** another chatbot.

Forge is **not** another LangChain wrapper.

Forge is **not** trying to compete with OpenHands, OpenClaw, LangGraph, CrewAI, Dify, or Harness.

Instead, Forge exists to answer one question:

> **How do modern AI agent platforms actually work under the hood?**

The project is intended to become an educational, production-quality platform that teaches AI systems engineering by implementing every important concept ourselves before relying on existing frameworks.

---

# Why Forge Exists

Modern AI engineering has become extremely high-level.

Most developers can build an agent by importing LangChain in minutes, but very few understand:

* how an agent runtime works
* how workflows execute
* how tools are scheduled
* how memory is implemented
* how retries work
* how observability works
* how tracing works
* how evaluation systems work
* how providers are abstracted
* how agent state is managed

Forge exists to bridge that gap.

The objective is not to build the biggest framework.

The objective is to understand **why frameworks are designed the way they are.**

---

# Primary Goal

Forge should teach its creator how companies like

* Harness
* OpenAI
* Anthropic
* LangGraph
* OpenHands
* Dify
* n8n
* Temporal

design AI systems.

By the end of the project, the creator should understand how to build an AI platform from scratch instead of only consuming frameworks.

---

# Philosophy

Forge follows one simple rule.

> Build the concepts.

Reuse the infrastructure.

We should build:

* Runtime
* Memory
* Planner
* Workflow Engine
* Agent SDK
* Tool System
* Event Bus
* Plugin System
* Observability
* Evaluation Engine

We should NOT reinvent:

* PostgreSQL
* Redis
* Docker
* FastAPI
* OpenTelemetry
* Kubernetes client
* GitHub SDK

Forge teaches AI engineering, not database engineering.

---

# What Forge Is NOT

Forge is NOT:

* another ChatGPT UI
* another AI chatbot
* another RAG demo
* another prompt playground
* another workflow clone
* another SaaS

Those may exist as demonstrations.

They are not the project.

---

# Think of Forge like this

Windows is not Microsoft Word.

Windows is an operating system.

Applications run on Windows.

Forge follows exactly the same philosophy.

Forge is the operating system.

Agents are applications.

Examples:

* Coding Agent
* DevOps Agent
* Research Agent
* GitHub Agent
* HomeLab Agent

These are examples built on Forge.

They are NOT Forge.

---

# Long-Term Goal

Someone should be able to install Forge and build any kind of agent without modifying the runtime.

For example:

```python
agent = Agent(
    model="gemini",
    planner="react",
    memory="vector",
    tools=[
        GitHub(),
        Filesystem(),
        Terminal()
    ]
)
```

Everything should be configurable.

Nothing should be hardcoded.

---

# Engineering Principles

Forge should always optimize for:

* simplicity
* modularity
* extensibility
* observability
* developer experience
* explicit architecture

Avoid unnecessary abstractions.

Introduce complexity only when it solves a real engineering problem.

---

# Design Philosophy

Every feature should answer one question:

> Does this help us understand AI systems better?

If not,

it probably doesn't belong.

---

# Architecture Philosophy

Forge should look like an operating system.

```
Forge

Runtime

Memory

Planner

Workflow Engine

Provider Layer

Tool Registry

Plugin System

Event Bus

Observability

Evaluation

SDK

CLI
```

Everything else builds on top.

---

# Runtime Philosophy

The runtime is the heart of Forge.

Everything should execute through it.

```
User

↓

Runtime

↓

Planner

↓

LLM

↓

Tool

↓

Observation

↓

Memory

↓

Next Step

↓

Final Response
```

Nothing bypasses the runtime.

---

# Provider Layer

Forge should never directly depend on OpenAI or Gemini.

Instead:

```
Provider Interface

↓

OpenAI

Gemini

Anthropic

Ollama

Azure OpenAI

Future Providers...
```

Switching providers should require configuration, not code changes.

---

# Memory Philosophy

Memory is more than embeddings.

Forge should eventually support multiple memory types.

Examples:

Short-term memory

Working memory

Conversation memory

Long-term memory

Semantic memory

User preferences

Future memory implementations should plug into the same interface.

---

# Planning Philosophy

Planning should be independent of execution.

Different planning strategies should be interchangeable.

Examples:

* ReAct
* Plan-and-Execute
* Reflection
* Tree Search
* Future planners

The runtime should not care which planner is used.

---

# Workflow Philosophy

Workflows should eventually support:

Sequential execution

Conditional execution

Loops

Parallel branches

Retries

Checkpoints

Pause / Resume

Human approval

Exactly like production workflow engines.

---

# Tool Philosophy

Everything is a Tool.

Examples:

Filesystem

GitHub

Docker

Browser

SSH

Slack

Kubernetes

Email

Google Calendar

Every tool should implement the same interface.

---

# Plugin Philosophy

Forge should be extendable without modifying the core.

Developers should be able to create:

* tools
* providers
* planners
* memory backends
* workflows

through plugins.

---

# Observability Philosophy

Observability is one of Forge's defining features.

Every action should be visible.

The platform should answer questions like:

What prompt was sent?

Which model responded?

Which tools were called?

Why was a tool selected?

How many retries happened?

How many tokens were used?

What was the latency?

How much did the request cost?

Why did execution fail?

What was the execution graph?

A production AI platform without observability is effectively impossible to debug.

---

# Evaluation Philosophy

Forge should eventually compare:

Prompt A vs Prompt B

Model A vs Model B

Planner A vs Planner B

Agent Version A vs Version B

Workflow Version A vs Version B

The platform should make experimentation easy.

---

# Learning Philosophy

Forge is a learning project.

Whenever introducing a new concept:

First:

Understand it.

Second:

Implement a minimal version.

Third:

Compare it against existing frameworks.

Only then consider integrating external libraries.

---

# Relationship with Existing Frameworks

Forge should learn from projects like:

LangGraph

OpenHands

OpenClaw

CrewAI

Mastra

Dify

Temporal

n8n

Harness

without copying them.

These projects are references, not templates.

---

# Libraries Strategy

Day 1:

Avoid LangChain and LangGraph.

Build core concepts manually.

After understanding the problems,

introduce adapters.

Eventually:

```
Forge Runtime

↓

Workflow

↓

Forge Planner

OR

LangGraph

↓

Execution
```

Forge should integrate with external ecosystems rather than depend entirely on them.

---

# Recommended Technology Stack

Backend

* Python
* FastAPI
* asyncio
* Pydantic
* SQLAlchemy

Frontend

* Next.js
* TypeScript
* React
* TailwindCSS
* shadcn/ui

Storage

* PostgreSQL
* Redis

Infrastructure

* Docker
* Docker Compose

Observability

* OpenTelemetry
* Structured Logging
* Metrics

---

# Repository Structure

```
forge/

apps/
    web/
    api/

packages/
    runtime/
    planner/
    sdk/
    memory/
    providers/
    workflows/
    tools/
    plugins/
    observability/
    evaluation/

examples/
    coding-agent/
    devops-agent/
    research-agent/

docs/

tests/

docker/
```

---

# Development Philosophy

Never ask:

"What feature should we build?"

Instead ask:

"What engineering concept should we understand next?"

Examples:

Week 1

Tool Calling

Week 2

Memory

Week 3

Streaming

Week 4

Planner

Week 5

Workflow Engine

Week 6

Tracing

Week 7

Evaluation

Week 8

Human-in-the-loop

Week 9

Plugin System

Week 10

Distributed Execution

Forge grows as knowledge grows.

---

# Success Criteria

Forge is successful if, after building it, its creator deeply understands:

* AI agent architecture
* Agent runtimes
* Workflow orchestration
* Prompt management
* Planning algorithms
* Memory systems
* Tool execution
* Provider abstraction
* Event-driven systems
* Async Python
* Observability
* Tracing
* Evaluation
* AI infrastructure
* Production AI engineering

The ultimate outcome is not merely a finished application, but becoming the kind of engineer who can design, build, debug, and extend modern AI platforms with confidence.

---

## One addition I'd make after thinking about this for a few weeks

I'd add a final guiding principle:

> **Forge should never hide complexity—it should explain it.**

If another AI framework acts as a black box, Forge should expose what's happening. Every tool call, planner decision, memory lookup, retry, and workflow transition should be inspectable. The platform itself should become the best way to *learn* AI agent engineering, not just to build AI agents.

I genuinely think **that** is what makes Forge different. It's not trying to be "another agent framework." It's trying to be the framework that teaches you *why* all the other frameworks are built the way they are. That's a vision I think is worth spending a year or more building.
