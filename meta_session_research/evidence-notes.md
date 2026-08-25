# Evidence Notes

Started: 2026-05-01

Purpose: record external guidance as research notes, not as proof of a
preselected architecture. These notes should be challenged during skeptic
review.

## OpenAI: GPT-5.5 Release And Model Docs

Sources:

- [Introducing GPT-5.5](https://openai.com/index/introducing-gpt-5-5/)
- [OpenAI API Models](https://developers.openai.com/api/docs/models)

Date observed: 2026-05-01.

Evidence note:

OpenAI released GPT-5.5 on 2026-04-23 and updated the release note on
2026-04-24 to say GPT-5.5 and GPT-5.5 Pro are available in the API. The model
docs list `gpt-5.5` as the flagship model for complex reasoning and coding, with
reasoning controls, a 1M context window, 128K max output, and tools including
functions, web search, file search, and computer use.

Research relevance:

This directly raises the burden of proof on Azoth's procedural scaffolding. If a
frontier model is explicitly designed for messy multi-step tool work, Azoth
should compare current harness behavior against a lighter GPT-5.5-first
baseline, not assume old orchestration needs still apply.

Confidence: high for model availability and positioning; medium for how this
will translate into this specific repo without benchmark runs.

## OpenAI: Agent Evals And Trace Grading

Sources:

- [Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals)
- [Trace grading](https://developers.openai.com/api/docs/guides/trace-grading)
- [Safety in building agents](https://developers.openai.com/api/docs/guides/agent-builder-safety)

Date observed: 2026-05-01.

Evidence note:

OpenAI recommends starting with traces while debugging agent behavior, then
moving to datasets and eval runs once "good" behavior is understood. The safety
guidance emphasizes tool approvals, guardrails, and trace graders/evals for
understanding and preventing mistakes.

Research relevance:

This supports the plan's trace-first method. The first research move should be
observability and case comparison, not immediate implementation or validator
expansion.

Confidence: high.

## Anthropic: Managed Agents

Source:

- [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)

Date observed: 2026-05-01.

Evidence note:

Anthropic frames long-horizon agents around separable brain, hands, harness,
sandbox, and durable session state. The key research pressure is that harness
assumptions can go stale as model behavior improves.

Research relevance:

This maps strongly onto the proposed "one strategic brain, many hands" pattern.
Azoth should distinguish enduring interfaces from model-steering assumptions
that may now be outdated.

Confidence: high.

## Anthropic: Context Engineering

Source:

- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

Date observed: 2026-05-01.

Evidence note:

Anthropic warns against both brittle over-specified prompts and vague prompts
that assume shared context. Their recommendation is concrete, organized,
task-fit context at the right altitude.

Research relevance:

Azoth's always-loaded doctrine and procedural command bodies should be measured
against generated context views and progressive disclosure. The issue is not
"less context" in the abstract; it is whether each token is earning its place.

Confidence: high.

## Anthropic: Building Effective Agents

Source:

- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)

Date observed: 2026-05-01.

Evidence note:

Anthropic distinguishes workflows from agents and recommends starting with the
simplest solution possible, adding complexity only when task performance
justifies the latency and cost tradeoff.

Research relevance:

Azoth should not use agentic machinery as a default virtue. The research must
ask which tasks benefit from governed workflows and which benefit from direct
model-led work.

Confidence: high.

## Anthropic: Multi-Agent Research System

Source:

- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)

Date observed: 2026-05-01.

Evidence note:

Anthropic reports that multi-agent systems are especially useful for breadth
research where independent parallel directions matter, but they have high token
cost and are less naturally suited to tightly coupled coding tasks. They also
recommend starting evals immediately with small representative samples.

Research relevance:

This supports using subagents selectively for research breadth, code
exploration, independent review, and disjoint implementation, while treating
mandatory stage swarms as something that must prove its value.

Confidence: high.

## Anthropic: Agent Skills

Source:

- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

Date observed: 2026-05-01.

Evidence note:

Skills package procedural knowledge in discoverable files and let agents load
deeper instructions only when needed.

Research relevance:

This supports testing whether Azoth's command and doctrine surface should move
toward skill-first progressive disclosure. The hypothesis is not that
procedural knowledge is bad; it is that always-on procedural bulk may be the
wrong delivery mechanism.

Confidence: high.

## Browser Use: Bitter Lesson Of Agent Frameworks

Source:

- [The Bitter Lesson of Agent Frameworks](https://browser-use.com/posts/bitter-lesson-agent-frameworks)

Date observed: 2026-05-01.

Evidence note:

Browser Use argues for a minimal agent loop, broad action space, explicit
completion signaling, ephemeral context management, and reliable infrastructure
instead of abstraction-heavy agent frameworks.

Research relevance:

This is the strongest anti-scaffolding source in the current set. It should be
treated as a valuable challenge, not as a complete answer. Azoth's research
should test whether broad action space plus runtime restriction beats command
choreography on real Azoth workflows.

Confidence: medium-high; strong engineering signal, but from a browser-agent
domain with its own incentives.

## Browser Use: Agent Freedom

Source:

- [What Happens When You Give your Agent Maximum Freedom](https://browser-use.com/posts/agent-freedom)

Date observed: 2026-05-01.

Evidence note:

Browser Use reports that models often follow training-shaped behavior over
prompt instructions, and that observing real behavior can reveal better support
surfaces than trying to predict every model path in advance.

Research relevance:

This supports runtime observation and guardrails over prompt walls. If Azoth
repeatedly sees models route around its intended surface, that may indicate a
missing or awkward hand, not merely model indiscipline.

Confidence: medium-high.

## HumanLayer: 12 Factor Agents

Source:

- [12 Factor Agents](https://www.humanlayer.dev/blog/12-factor-agents)

Date observed: 2026-05-01.

Evidence note:

The 12 Factor Agents guide emphasizes owning prompts, context, control flow,
execution state, pause/resume, human contact, and small focused agents.

Research relevance:

This supports preserving Azoth's durable state, human gates, and pause/resume
ambitions while questioning whether the current implementation is too
ceremonial.

Confidence: medium-high.

## Initial Evidence Tension

The external guidance does not say "delete the harness." It says:

- strong models can carry more ambiguous work themselves;
- harness assumptions age;
- context should be curated rather than dumped;
- durable state, observability, tool approvals, and trace grading matter;
- multi-agent orchestration is useful when breadth or isolation earns the cost;
- explicit completion and pause/resume are important;
- runtime infrastructure is different from intelligence scaffolding.

Batch 0 research should therefore compare harness profiles instead of arguing
from aesthetics.

