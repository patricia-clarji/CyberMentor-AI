# Sentinel intelligent mentor

Sentinel is an adaptive cybersecurity mentor, not a general-purpose chat surface. Its stable personality is professional, patient, strict, encouraging, evidence-based, and focused on learner reasoning. The application selects a pedagogical mode and intervention before any configured model runs.

## Adaptation and memory

The mode set is teaching, explanation, guided practice, Socratic, hint, reflection, investigation, review, assessment support, safety redirect, and human review recommendation.

The deterministic adaptation engine can ask a question, give a hint, use an analogy, review a prerequisite, or recommend a lesson, lab, replay, reassessment, project, break, mission, or instructor review. Its decision uses tenant-scoped skill mastery, weak and strong skills, completed labs and missions, learner notes, hint use, portfolio evidence, current lesson/lab/mission/project state, recent failures and improvements, study streak, review schedule, confidence, independence, pace, and explanation preferences.

Sentinel stores only learning-relevant memory. It persists conversations, mode decisions, interventions, feedback, misconceptions, learner estimates, and recommendations. It does not intentionally collect unrelated personal information. Unsafe input and apparent secrets are not stored verbatim; only a one-way hash and policy category are logged.

Misconception evidence covers memorization without understanding, Linux syntax confusion, network-model confusion, SIEM query misunderstanding, treating an IOC as a verdict, incorrect investigation order, confirmation bias, missing evidence, and premature conclusions. Each record carries confidence, first and last observation, supporting evidence, status, and resolution time.

## Grounding and safety

Retrieval is restricted to published, verified, learner-visible content and approved reference metadata. Grading checks, answer keys, hidden mission evidence, and expert solutions are excluded. Retrieval queries/results and citation provenance are stored with `soc-reviewed-hybrid-2.0.0`.

The prompt includes only the authenticated learner's context. Every database context query is organization- and user-scoped. Lab and mission context includes learner-visible progress, attempts, mistakes, hints, notes, and actions, but excludes hidden evidence and solutions.

Sentinel refuses prompt injection, answer-key and grading-bypass requests, mission/lab solution requests, unauthorized real-target activity, credential theft, malware, destructive payloads, and apparent secret material. Provider output receives a second answer-leakage check. Safety policy selection does not depend on a model.

## Provider configuration

Set `CYBERMENTOR_LLM_PROVIDER` to one of:

- `openai`
- `anthropic`
- `google`
- `ollama`
- `mock`
- `deterministic`

The remaining settings are `CYBERMENTOR_LLM_API_KEY`, `CYBERMENTOR_LLM_BASE_URL`, `CYBERMENTOR_LLM_MODEL`, `CYBERMENTOR_LLM_TIMEOUT_SECONDS`, `CYBERMENTOR_LLM_TEMPERATURE`, `CYBERMENTOR_LLM_INPUT_COST_PER_MILLION`, and `CYBERMENTOR_LLM_OUTPUT_COST_PER_MILLION`.

No key is required for Ollama, mock, or deterministic mode. A missing/unavailable provider, network failure, invalid response, or output-leakage failure falls back to deterministic grounded mentoring. Changing providers requires configuration only.

Sentinel records prompt version `sentinel-mentor-2.0.0`, retrieval version, provider, model, temperature, prompt/completion token use, latency, estimated cost, and fallback state.

## Evaluation and operator expectations

The evaluation helper measures groundedness, hallucination risk, citation quality, unsafe-refusal accuracy, answer leakage, unsafe detail, latency, estimated cost, and keyword correctness. Unit and integration tests cover provider switching, mode selection, misconceptions, memory, history, feedback, retrieval exclusions, prompt injection, answer-key refusal, unsafe refusal, cross-tenant isolation, roadmap recommendations, and prompt/usage provenance.

The UI shows conversation history, pedagogical and delivery modes, reviewed citations, a concise adaptation rationale, related skills, recommended action, loading/progressive rendering, retry, copy, and feedback. It provides selectable course, lesson, lab, mission, project, assessment, and general contexts.

Current constraints:

- Progressive rendering begins after the API returns a complete response; provider-native server-sent streaming is not implemented.
- Retrieval is lexical over the currently approved corpus; embeddings remain a future enhancement.
- Learner confidence, independence, difficulty, and misconceptions are bounded heuristics, not clinical or psychometric assessments.
- Provider responses are protected by grounding and leakage checks, but cannot be proven error-free; citations and deterministic fallback remain visible.
- Portfolio advice uses only stored submissions and human review evidence, and never claims achievements that are absent.
