# Verification record — 5 November 2026

## Follow-up — 6 November 2026: translation setup fixed

The user's configured token successfully retrieved the pinned IndicTrans2 source and weights. Source inspection and its hashes are recorded in `code_review.md` and `model_metadata.json`. The missing-Torch error came from the Windows UI environment: the combined model dependency install failed while building IndicTransToolkit, because Microsoft C++ Build Tools are absent.

Translation now runs in an isolated Python 3.10 WSL CPU worker, using Torch 2.5.1+cpu, Transformers 4.49.0 and the official IndicTransToolkit 1.1.1 Linux wheel. Its dependency check passed. The Windows UI selects it using `TRANS_URL=http://127.0.0.1:8766`, and the adapter checks the returned checkpoint ID and revision. No Windows system compiler was installed. The worker is intentionally left running for the user; the existing Streamlit process needs a restart to reload configuration.

Five real public-example translations completed without runtime or deterministic-validation errors. Examples include `मुझे घर जाना है।` → `I have to go home.` and `मैंने अपना असाइनमेंट जमा नहीं किया है।` → `I have not submitted my assignment.` A separate real-model Streamlit AppTest clicked **Translate to English** and passed. Actual outputs, timing and readiness are saved in `translation_worker_verification.json`. This is not human adequacy/fluency validation or a new held-out benchmark.

An observed limitation remains: splitting translation around immutable spans produced `Naman The 12 November The report was submitted.` for `Naman ने 12 November को रिपोर्ट भेजी थी।`. Exact names/numbers were retained, but grammar and the distinction between sending and submitting need human review. Lexical validation did not catch this; the existing segmentation warning is warranted. No claim of full semantic correctness is made.

The final unit/UI suite after adding the worker contained 30 passing tests, including checkpoint-mismatch rejection. Param1 pretrained generation remains unverified due to available memory. The dated results below describe the earlier run and its blockers at that time.

This report separates application checks, model integration checks and model quality. No unit-test double is used in production adapters or evaluation predictions.

## Application checks

- 28 pytest tests passed in the installed UI environment (final complete suite: 8.03 seconds). Tests cover Unicode, whitespace, protected-span restoration and overlaps, URLs/email/code/numbers, empty/long input, Hindi passthrough, independent routing, unavailable models, rejected outputs, metric arithmetic, meaningful preservation denominators, dataset counts and actual Streamlit script interactions.
- Streamlit 1.51.0 launched successfully at `http://127.0.0.1:8501`. The page returned HTTP 200 and `/_stcore/health` returned `ok`.
- Streamlit AppTest exercised initial render, an empty-input action, Hindi-only basic conversion and Clear/reset. It is not a browser visual inspection. No browser automation tool was available.
- A separate live integration check exercised worker readiness and the actual conversion button against the loaded IndicXlit worker and produced `मुझे घर जाना है` from `mujhe ghar jana hai`, without test doubles (`live_ui_check.json`).
- Temporary UI and worker servers were stopped after verification; use the README commands to start them again. Downloaded weights remain in the external cache.
- `pip check` reports no broken requirements in `.venv`. `compileall` succeeded for the source, application and scripts.
- `requirements-ui.lock.txt` records the installed UI dependency versions. The corrected model dependency set completed pip dry-run resolution on Windows; this does not verify native build or inference compatibility.

## Actual model access / integration

See `model_metadata.json`, `code_review.md` and `integration_verification.json`.

| Component | Observed evidence | Remaining work |
| --- | --- | --- |
| IndicXlit | Official v1.0 weights loaded on CPU through the supplied Fairseq class; real word candidates, representative sentence conversions and two held-out runs completed | Contextual generation still requires Param1; basic quality limitations are measured below |
| Param1 | Checkpoint public and revision resolved; custom Python/config downloaded and inspected; real tokenizer/chat template loaded with Transformers 4.49.0 (25 tokens in the probe); adapter refused weight allocation with about 1 GiB available RAM | Run pretrained generation on hardware with sufficient available memory |
| IndicTrans2 | Metadata resolved; MIT LICENSE retrieved; protected config/code returned HTTP 401; metadata disables hosted inference | Accept gated access in user's HF account, provide token locally, inspect pinned source and run translation |

IndicXlit is the only pretrained model whose weights were loaded and inference verified. Param1's tokenizer/chat template was loaded without its pretrained weights. No Param1 or IndicTrans2 generation is claimed. The Transformers pool's `cold_load_seconds` remains empty; IndicXlit startup is measured separately in `indicxlit_artifact.json`. Model-unavailable behavior is operational. No model weights or private token were committed or published.

Hardware: Python 3.11.5, Windows build 26200; RAM 16,803,041,280 bytes, free memory varied during work and remained below the Param1 CPU guard. Existing PyTorch reports CPU-only and CUDA unavailable, so there is no detected CUDA GPU memory to report. Ubuntu/WSL offers Python 3.10.12 and roughly 7.6 GiB RAM.

## Recorded evaluation

Both 50-case runs saved actual outputs and errors. Basic mode (`evaluation-basic/`) completed 35/50 requested actions: 34 generated cases were scored, and one successful Hindi passthrough was excluded from model quality. IndicXlit responded in 43 cases, including drafts in pipelines whose later stages failed. Nine other attempts with model drafts were rejected by validation or failed later stages; remaining attempts required unavailable models or no model.

| Basic-mode measurement | Actual result / denominator |
| --- | --- |
| Requested-action completion | 35/50 (70%); includes one passthrough |
| CER | 0.0912257, macro mean over 34 completed generated cases |
| WER | 0.2130252, same 34 cases |
| Normalized exact match | 15/34 = 44.12% |
| Protected / numerical preservation | 5/5 eligible completed generated cases with protected spans, and 4/4 with numeric content; cases without those features and unsuccessful cases are excluded. Exact lexical checks do not prove named-entity or semantic quality. |
| English chrF / human quality | Unmeasured; no completed English model output or human review |
| Raw IndicXlit diagnostic CER / WER / exact match | 0.26953 / 0.39006 / 0.18605 over 43 drafts, including failed downstream actions; references target Natural Hinglish rather than raw word transliteration, so denominators/task differ |

Context mode (`evaluation-context/`) completed one model-free passthrough; all 49 other requested actions remained incomplete due to unavailable contextual/rewriting models, validation or later pipeline stages. IndicXlit still responded in 43 cases and its drafts are retained. Contextual CER/WER/exact match and English chrF are null because there are no completed generated contextual outputs. Fallback drafts never count as successful contextual processing.

`failure_analysis.md` and each run's `failure_analysis.json` contain actual inputs/tasks/outputs, draft references and next steps. Observed basic errors include `tum → टम`, `pe → पीई`, informal auxiliaries and negation spellings. `mat → मैट` was caught by the guard; `nhi → न्ही` demonstrates a gap in abbreviation coverage. `nahi → नही` triggered a conservative possible-negation-loss rejection, even though this may be a spelling issue rather than semantic loss. Formal rewriting, contextual meaning preservation and translation remain unverified. `end_to_end_examples.json` records all eight requested representative attempts, including blocked tasks.

Measured IndicXlit first startup was 539.845 seconds including download/extraction/load. A separate restart with the cached artifact took 15.167 seconds. In the final basic run (four worker CPU threads), mean warm worker request time was 0.5380 seconds across 43 requests; requests contain different numbers of words and include local HTTP overhead. Mean end-to-end attempt duration was 0.4658 seconds over all 50 attempts, including fast failures; it is not successful full-pipeline latency. Param1/IndicTrans2 cold/warm latency and a three-model ablation remain unmeasured. Human adequacy, fluency and meaning/tone/tense reviews remain null. Draft references have not received human validation.

## Observed failures and corrections during implementation

- The globally installed Streamlit 1.30 AppTest could not serialize a radio control with formatted values. The UI now uses plain displayed values with a separate internal mapping; checks run on pinned 1.51.0.
- A three-second AppTest default timeout was insufficient on the loaded machine; UI checks explicitly allow 60 seconds. Latest checks passed.
- Initial evaluation counted partial outputs from failed pipelines as exact matches. The runner now excludes unsuccessful/partial results from quality scoring, records denominators, and does not score model-free passthrough as model quality.
- The older Fairseq package and Param1's old-style custom class require separate dependency environments. These were identified by source inspection; no silent substitute model was introduced.

## Assessment status

Application, safeguards, unit/UI tests, structured dataset, evaluator, real IndicXlit inference and basic evaluation are implemented. Param1 pretrained generation, IndicTrans2 translation and their quality assessment remain incomplete. This repository must not be described as a fully verified three-model generative demonstration until those blockers are resolved and actual reports include successful measured runs.
