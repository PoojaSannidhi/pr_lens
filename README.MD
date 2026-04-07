---
title: pr-lens
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: false
---

# 🔍 PR Lens — Multi-Agent GitHub PR Review System

> Parallel, agent-driven pull request analysis system that performs structured code review using specialized AI agents, guardrails, and typed outputs.

---

## 🧠 Overview

PR Lens is a **multi-agent AI system** designed to analyze GitHub pull requests with depth, structure, and reliability.

Instead of relying on a single LLM call, PR Lens decomposes the problem into **specialized agents** that operate concurrently:

- **Summary Agent** explains what changed and why  
- **Security Agent** identifies vulnerabilities and risks  
- **Quality Agent** evaluates maintainability and code health  
- **Synthesis Agent** merges outputs into a final structured report  

The system leverages the **OpenAI Agents SDK** to orchestrate execution, enforce guardrails, and produce strongly-typed outputs.

---

## ⚙️ System Architecture

```
User Input (PR URL)
        │
        ▼
   Triage Agent (streamed execution)
        │
        ├── Input Guardrail (validates PR URL before LLM usage)
        │
        ├── Metadata Tool (GitHub API)
        │
        ├── Parallel Analysis (asyncio.gather)
        │     ├── Summary Agent
        │     ├── Security Agent
        │     └── Quality Agent
        │
        └── Handoff → Synthesis Agent
                  │
                  ├── Output Guardrail (schema enforcement)
                  ├── Structured Output (Pydantic)
                  └── Optional Email Delivery (SendGrid)
```

---

## 🚀 Key Capabilities

### 🔹 Multi-Agent Decomposition
Breaks complex PR analysis into **independent expert agents**, improving depth and specialization.

### 🔹 Parallel Execution
All specialist agents execute concurrently using `asyncio.gather`.

**Result:** Total latency ≈ slowest agent (not sum of all agents)

### 🔹 Streaming Orchestration
Uses `Runner.run_streamed()` to provide **real-time execution visibility**.

### 🔹 Tool-Augmented Reasoning
Agents use structured tools like GitHub APIs and email delivery.

### 🔹 Guardrails for Reliability
- Input Guardrail prevents invalid inputs  
- Output Guardrail enforces schema correctness  

### 🔹 Typed Outputs
All outputs follow **Pydantic schema**, eliminating fragile parsing.

---

## 🧩 Why Multi-Agent Architecture?

Pull request analysis requires **multiple perspectives**:

- Functional understanding  
- Security reasoning  
- Code quality evaluation  

A single LLM struggles with all three simultaneously.

PR Lens solves this with:
- Specialized agents  
- Parallel execution  
- Structured synthesis  

---

## ⚡ Performance Design

- Parallel execution via `asyncio.gather`  
- Tool-wrapped concurrency to bypass LLM sequential limits  
- Streaming improves UX responsiveness  

---

## 🛡️ Reliability & Safety

- Guardrails prevent invalid inputs and malformed outputs  
- Typed schemas ensure consistent handling  
- No brittle string parsing  

---

## 🗂️ Project Structure

```
pr_lens/
├── app.py
├── pr_agents/
├── tools/
├── models/
└── utils/
```

---

## ⚠️ Limitations

- GitHub API rate limits (60 req/hr unauthenticated)  
- LLM-based analysis may miss deep semantic bugs  
- Parallel agents increase token usage and cost  

---

## 🛠️ Tech Stack

- OpenAI Agents SDK  
- Gradio  
- GitHub REST API  
- Pydantic  
- SendGrid (optional)

---

## ▶️ Running Locally

```
git clone https://github.com/yourname/pr_lens.git
cd pr_lens
pip install -r requirements.txt
python app.py
```

---

## 💡 Future Improvements

- Persistent memory for PR history  
- Static analysis tool integration  
- Private repo support  
- PR scoring system  

---

## 📄 License

MIT
