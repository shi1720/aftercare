# Aftercare agent registration

The runnable multi-agent configuration is `gitlab/flows/aftercare.yml`. Its
AgentComponents are created by the flow. This Markdown file is explanatory;
it is not a GitLab agent schema or a registered AI Catalog item.

Create a custom flow in the project's **AI > Flows**, paste that YAML, enable it,
and configure a **Mention** trigger. Mention the actual generated service-account
username on an issue asking it to investigate the checkout contract. Save the
real flow session and CI pipeline links. Merely checking in YAML is not execution.

The checked-in checkout fixture is deliberately defective. Main's CI demonstrates
the expected failure; branches beginning `aftercare/repair-` verify an independent
AI source repair and enforce changed-file boundaries. This integration is
supervised: it opens a tested MR and does not merge or deploy it automatically.

The local dashboard is a separate deterministic sandbox reference execution.
Its fixed repair is not presented as an LLM-generated edit. Real external systems
require explicit adapter integration and deployment credentials.
