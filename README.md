# maskman
# MaskMan – AI Powered Product Comparison & Price Intelligence Platform

## Overview
MaskMan is a full-stack AI-powered product comparison platform designed to help users discover, compare, and analyze products across multiple e-commerce platforms.

The project combines:
- AI-driven product discovery
- Intelligent product matching
- Web scraping
- Backend APIs
- Asynchronous task processing
- Vector embeddings and AI services

This project demonstrates practical experience in backend engineering, AI integration, automation workflows, and scalable application architecture.

---

# Features

## Product Discovery
- Search and discover products from multiple e-commerce platforms
- Intelligent product matching across websites
- Unified product comparison system

## AI Integration
- AI-powered recommendation and matching system
- Embedding-based similarity handling
- Agent-based architecture for product discovery workflows

## Web Scraping Engine
- Amazon scraper integration
- Flipkart scraper integration
- Automated product data collection
- Dynamic scraping workflow management

## Backend System
- REST API architecture
- Authentication & admin modules
- Secure API routing
- Background task execution using Celery

## Data & Processing
- Product repository management
- Price tracking and updates
- Automated data fixing and migration scripts
- Async processing pipelines

---

# Tech Stack

## Backend
- Python
- FastAPI
- Celery
- Supabase

## AI / ML
- Embeddings
- AI Agents
- Product Matching Logic

## Database & Storage
- Supabase Database
- Vector-based similarity workflows

## Scraping & Automation
- Custom scraping engine
- Amazon & Flipkart scrapers
- Async task workers

---

# Project Architecture

```text
User Request
     ↓
FastAPI Backend
     ↓
AI Discovery & Matching Services
     ↓
Scraping Engine
     ↓
Amazon / Flipkart Product Data
     ↓
Product Repository & Database
     ↓
Comparison & Recommendations
```

---

# Folder Structure

```text
backend/
 ├── api/                 # Authentication & API routes
 ├── db/                  # Database sessions & repositories
 ├── scrapers/            # Amazon & Flipkart scraping engine
 ├── services/            # AI agents & matching services
 ├── worker/              # Celery background workers
 ├── scripts/             # Migration & automation scripts
 └── main.py              # Application entry point
```

---

# Key Learning Outcomes

This project helped strengthen understanding of:
- Backend system design
- API development with FastAPI
- AI service integration
- Asynchronous task processing
- Scalable scraper architecture
- Data handling and automation workflows
- Real-world software engineering practices

---

# Future Improvements

- Add React frontend dashboard
- Improve recommendation quality using advanced embeddings
- Add real-time price alerts
- Integrate more e-commerce platforms
- Add analytics dashboard
- Improve deployment and monitoring pipeline

---

# Installation

## Clone Repository

```bash
git clone <your-repository-link>
cd maskman
```

## Create Virtual Environment

```bash
python -m venv venv
```

## Activate Environment

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Run Backend Server

```bash
uvicorn backend.main:app --reload
```

---

# Resume Highlights

- Built an AI-powered product comparison platform using FastAPI and AI services.
- Developed scraping pipelines for Amazon and Flipkart.
- Implemented agent-based product discovery and matching workflows.
- Designed asynchronous processing pipelines using Celery.
- Integrated embeddings and intelligent product similarity workflows.

---

# Why This Project Matters

MaskMan demonstrates:
- Real backend engineering skills
- AI integration capabilities
- Automation workflows
- System architecture understanding
- Practical software development experience

This project reflects the ability to build production-oriented systems beyond tutorial-level applications.

