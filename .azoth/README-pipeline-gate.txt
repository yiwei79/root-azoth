Runtime gates (D50) — local state only
--------------------------------------
Do not commit `.azoth/scope-gate.json` or `.azoth/pipeline-gate.json`. They are gitignored.
Copy from the committed examples when you need a template:

  scope-gate.json.example   — written by /next on human approval; shape for scope-gate.json
  pipeline-gate.json.example — shape written by /deliver-full, /auto, or /deliver Stage 0
    when scope-gate.json has delivery_pipeline: governed or target_layer: M1. Copy fields from
    your active scope-gate session_id and expires_at; set pipeline to deliver-full | auto | deliver.

The committed *.example files are illustrative only; runtime JSON is local and session-specific.
