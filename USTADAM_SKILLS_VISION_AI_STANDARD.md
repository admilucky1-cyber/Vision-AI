# Ustadam Skills → Vision AI Engineering Standard
**Version:** 1.0.0  
**Date:** 2026-09-14  
**Status:** Production Standard  
**Applies to:** Vision AI v5.8.1 and all future versions  

This document converts every major learning point from Ustadam courses (Programming Fundamentals C++, OOP, Python MasterClass, Data Science, Web Development) into concrete, enforceable engineering skills for the Vision AI project.

Use this document as:
- The official coding & architecture standard
- The learning roadmap for anyone joining the project
- The checklist before merging any new feature

---

## 1. Core Philosophy (from Ustadam)

1. **Demystify complexity** — code must be understandable by a junior developer after reading it once.
2. **Logic Building first** — solve the pure logic before integrating into the system.
3. **Progressive construction** — every feature grows from small, working pieces.
4. **Real-world focus** — every abstraction must serve a real product need.
5. **Separate concerns cleanly** — Data Layer, Business Logic, UI/API must stay independent.

---

## 2. Skill Map: Ustadam → Vision AI

| Ustadam Source              | Core Skill                              | Vision AI Application Area                  |
|----------------------------|-----------------------------------------|---------------------------------------------|
| Programming Fundamentals   | Logic Building, Functions, Decision Making | Services, pure helpers, route handlers     |
| OOP Principles             | Encapsulation, Composition, Domain Models | `services/`, models, repositories          |
| Python MasterClass         | Clean Python, structure, readability    | All `.py` files                            |
| Data Science               | DataFrame thinking, clean presentation  | Admin tables, usage, jobs, analytics       |
| Web Course                 | Semantic HTML, CSS architecture, REST, JS modularity | Frontend + API contracts              |

---

## 3. Mandatory Engineering Rules

### 3.1 Logic Building Rule (from C++ PF)
- Every non-trivial piece of logic must first exist as a pure function or small class with clear Input → Process → Output.
- No business logic inside FastAPI route functions.
- Prefer early returns and guard clauses over deep nesting.

**Example pattern:**
```python
def calculate_quota_status(user: User, usage: list[UsageEvent]) -> QuotaStatus:
    """Pure logic. No side effects. Easy to unit test."""
    ...
```

### 3.2 Independent Data Layer + Encapsulation (from OOP)
- Database access only through dedicated service or repository functions.
- Route handlers may only call services.
- Models contain data + simple validation. Complex behavior lives in services.
- Never leak SQLAlchemy session or raw queries into routes or frontend contracts.

### 3.3 Python Quality Standard (from Python MasterClass)
- Full type hints on all public functions and class methods.
- Short, intentional docstrings (focus on *why* and contracts).
- Modules must have single responsibility.
- Constants and enums instead of magic strings/numbers.
- Prefer composition: inject dependencies rather than hard-coding.

### 3.4 DataFrame Mindset (from Data Science)
Any list of records shown to the user (usage, jobs, users, skills, chat history) must support:
- Clear columns
- Filtering
- Sorting
- Searching
- Empty state
- Loading state
- Error state

Backend should return clean, ready-to-render data. Frontend only displays.

### 3.5 Web & Frontend Standard (from Web Course)
- All pages share a consistent semantic shell (`header`, `nav`, `main`, `aside`, `footer`).
- CSS follows strict layers: Tokens → Base → Layout → Components → Utilities → Pages.
- Design tokens (colors, spacing, radii, fonts) live in one place.
- JavaScript is modular. Large files must be split by responsibility.
- One shared API client layer for all frontend → backend communication.
- REST endpoints follow resource-oriented design and consistent response shape.

---

## 4. Project Structure Rules

```
vision-ai/
├── main.py                 # App factory + middleware only
├── routes/                 # Thin route handlers only
├── services/               # All business logic + data access
├── models/ or services/models_db.py
├── frontend/
│   ├── index.html, studio.html, ...
│   └── static/
│       ├── css/            # tokens.css first, then layered files
│       └── js/             # modular files + shared api.js / ui.js
├── tests/
└── ...
```

**Hard rule:** New business logic goes into `services/`. Routes stay thin.

---

## 5. Feature Development Workflow (Ustadam Style)

For every new feature follow this sequence:

1. **Logic Building**  
   Write pure functions / small classes that solve the core problem. Unit test them.

2. **Lab Manual**  
   Integrate into a service. Add clear types and docstring.

3. **Programming Day Tasks**  
   Expose via thin route + consistent REST response.

4. **Challenge Yourself**  
   Handle edge cases, empty data, errors, rate limits, auth.

5. **Vision to Reality**  
   Connect to frontend with proper loading / empty / error states and clean UI.

---

## 6. Concrete Implementation Priorities (Ordered)

| Priority | Skill Source          | Action                                      | Impact                          |
|----------|-----------------------|---------------------------------------------|---------------------------------|
| P0       | OOP + Python          | Enforce service layer on all routes         | Architecture integrity          |
| P1       | Data Science + Web    | Reusable DataTable (backend + frontend)     | Consistent admin & studio UX    |
| P2       | Web + CSS             | Extract design tokens + semantic page shell | Maintainable UI                 |
| P3       | JavaScript            | Modularize large JS files + shared API client | Long-term frontend health     |
| P4       | Fundamentals          | Add pure-logic unit tests for critical paths | Reliability                     |

---

## 7. Coding Checklist (Must pass before merge)

- [ ] Business logic is in `services/`, not in routes
- [ ] Public functions have type hints and short docstrings
- [ ] No deep nesting; early returns used
- [ ] Data returned to frontend is clean and ready to display
- [ ] New tables/lists support filter / sort / search / empty / loading states
- [ ] Frontend changes respect semantic HTML and existing CSS token system
- [ ] API follows consistent response shape and correct HTTP status codes
- [ ] At least one pure unit test exists for the new core logic

---

## 8. Learning Path for Contributors

1. Read this document completely.
2. Study one existing clean service (e.g. usage or settings related).
3. Implement a small pure function following the Logic Building rule.
4. Add a thin route that uses it.
5. Connect it to the frontend with proper states.
6. Submit for review against the checklist above.

---

## 9. Versioning of this Standard

- This file lives in the project root as `USTADAM_SKILLS_VISION_AI_STANDARD.md`
- Any change to the standard requires a version bump and a short changelog entry at the top.
- All future major refactors must reference which section of this standard they implement.

---

**This is now the official engineering and learning standard for Vision AI.**

Next concrete build step (ready to execute immediately):
- Implement Priority P0 + P1 (service-layer enforcement + reusable DataTable foundation)
- or generate the full design-token + semantic shell upgrade
- or modularize the largest JavaScript files

State which priority you want executed first and the work will begin.