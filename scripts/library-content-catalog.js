// Curated catalog. Order here = order on the shelf.
// Restructured 2026-06-26 per docs/plans/library-restructure-2026-06-26.md
// 8 categories, 64 entries, journeys, featured roles, and group ribbons.

export const CATALOG = {
  "statuses": {
    "proposed": {
      "label": {
        "en": "Proposed",
        "zh": "提出"
      },
      "gloss": {
        "en": "A conjecture we intend to test; no evidence yet.",
        "zh": "我们打算测试的猜想；目前尚无证据。"
      },
      "color": "#a855f7"
    },
    "supported": {
      "label": {
        "en": "Supported",
        "zh": "支持"
      },
      "gloss": {
        "en": "Evidence-backed but not formally proven.",
        "zh": "有证据支持但尚未形式化证明。"
      },
      "color": "#22c55e"
    },
    "open": {
      "label": {
        "en": "Open",
        "zh": "待定"
      },
      "gloss": {
        "en": "Under active investigation; could go either way.",
        "zh": "正在积极调查中；结果尚不确定。"
      },
      "color": "#3b82f6"
    },
    "refuted": {
      "label": {
        "en": "Refuted by us",
        "zh": "被我们否证"
      },
      "gloss": {
        "en": "We tested it and falsified it ourselves.",
        "zh": "我们已测试并自行证伪。"
      },
      "color": "#ef4444"
    },
    "self-corrected": {
      "label": {
        "en": "Self-corrected",
        "zh": "自我纠正"
      },
      "gloss": {
        "en": "We published it, then found a confounder and retracted the strong form.",
        "zh": "我们发表后发现了混淆因素，并撤回了较强形式。"
      },
      "color": "#f59e0b"
    },
    "proven": {
      "label": {
        "en": "Proven (Lean)",
        "zh": "已证明"
      },
      "gloss": {
        "en": "Backed by a machine-checked Lean proof.",
        "zh": "由机器检查的 Lean 证明支持。"
      },
      "color": "#14b8a6"
    },
    "live": {
      "label": {
        "en": "Live evidence",
        "zh": "Live evidence"
      },
      "gloss": {
        "en": "Continuously refreshed evidence (live-lab canary).",
        "zh": "持续刷新的证据（实时实验室金丝雀）。"
      },
      "color": "#06b6d4"
    }
  },
  "categories": [
    {
      "id": "foundations",
      "label": {
        "en": "Foundations & Vision",
        "zh": "基础与愿景"
      },
      "blurb": {
        "en": "Orientation, shared vocabulary, data provenance, and the research agenda. Start here if you are new.",
        "zh": "方向、共享词汇、数据来源与研究议程。如果你是新来的，从这里开始。"
      }
    },
    {
      "id": "conjectures",
      "label": {
        "en": "Conjectures & Proofs",
        "zh": "猜想与证明"
      },
      "blurb": {
        "en": "Every claim we have tested, its lifecycle status, and the evidence behind it. The hypothesis ledger.",
        "zh": "我们测试过的每个声明、其生命周期状态及其背后的证据。假设台账。"
      }
    },
    {
      "id": "methods",
      "label": {
        "en": "Methods & Theory",
        "zh": "方法与理论"
      },
      "blurb": {
        "en": "How we measure, bound, and reason about potential error — from sloppy-model geometry to Bayesian active learning.",
        "zh": "我们如何测量、界定和推理势函数误差 — 从 sloppy-model 几何到贝叶斯主动学习。"
      }
    },
    {
      "id": "validation",
      "label": {
        "en": "Validation & Evidence",
        "zh": "验证与证据"
      },
      "blurb": {
        "en": "Benchmarks, live-lab results, and the MLIP flywheel evidence chain.",
        "zh": "基准测试、实时实验室结果以及 MLIP 飞轮证据链。"
      }
    },
    {
      "id": "formalization",
      "label": {
        "en": "Formalization",
        "zh": "形式化"
      },
      "blurb": {
        "en": "Lean-backed theorem proofs, build-locking contracts, and the formal proof ledger.",
        "zh": "Lean 支持的定理证明、构建锁定契约以及形式化证明台账。"
      }
    },
    {
      "id": "changelog",
      "label": {
        "en": "Progress Log",
        "zh": "进展日志"
      },
      "blurb": {
        "en": "What changed, why, and what is next. The narrative spine of the project.",
        "zh": "改变了什么、为什么以及下一步是什么。项目的叙事主线。"
      }
    },
    {
      "id": "references",
      "label": {
        "en": "Reviews & References",
        "zh": "评议与参考文献"
      },
      "blurb": {
        "en": "The literature we build on, the funding context, and the adversarial reviews our claims passed before going public.",
        "zh": "我们所依据的文献、资金背景以及我们的声明在公开前通过的对抗性评议。"
      }
    },
    {
      "id": "operations",
      "label": {
        "en": "Build & Operations",
        "zh": "构建与运营"
      },
      "blurb": {
        "en": "How this library was built and how to reproduce every result. Extraction logs, ADRs, and operational fabric.",
        "zh": "该图书馆是如何构建的，以及如何复现每个结果。提取日志、架构决策记录和运营结构。"
      }
    }
  ],
  "languages": {
    "en": {
      "label": "English",
      "native": "English"
    },
    "zh": {
      "label": "Chinese",
      "native": "中文"
    }
  },
  "journeys": [
    {
      "id": "new-here",
      "label": {
        "en": "I'm new here",
        "zh": "初次访问"
      },
      "description": {
        "en": "Start with the big picture.",
        "zh": "从全局开始。"
      },
      "path": [
        "what-is-an-interatomic-potential",
        "readme",
        "glossary",
        "error-geometry-objects",
        "conjecture-ledger",
        "hyp-hyper-ribbon-universality",
        "mlip-cloud-baseline-distill",
        "research-evolution"
      ]
    },
    {
      "id": "materials-scientist",
      "label": {
        "en": "Show me the physics",
        "zh": "展示物理"
      },
      "description": {
        "en": "Evaluate the claims against the evidence.",
        "zh": "根据证据评估声明。"
      },
      "path": [
        "data-provenance",
        "sloppy-models",
        "error-geometry-objects",
        "hyp-hyper-ribbon-universality",
        "hyp-cross-mlip-orthogonal-errors",
        "projection-law-round2-results",
        "layer2-research-paper",
        "academic-review-projection-law",
        "references"
      ]
    },
    {
      "id": "mlip-builder",
      "label": {
        "en": "I build MLIPs",
        "zh": "我构建 MLIP"
      },
      "description": {
        "en": "Understand the flywheel, the operator, and how to reproduce results.",
        "zh": "理解飞轮、算子以及如何复现结果。"
      },
      "path": [
        "working-papers",
        "mlip-cloud-baseline-distill",
        "mlip-ni-paired-accuracy-live",
        "mlip-mptrj-broad-dft-canary",
        "projection-law-round2-preregistration",
        "projection-law-round2-results",
        "bayesian-active-learning",
        "gnn-error-prediction",
        "reproduce"
      ]
    },
    {
      "id": "funder-reviewer",
      "label": {
        "en": "Is this rigorous?",
        "zh": "这是否严谨？"
      },
      "description": {
        "en": "Assess epistemic discipline and formal backing.",
        "zh": "评估认识论纪律和形式化支持。"
      },
      "path": [
        "internal-science-program",
        "methodology",
        "conjecture-ledger",
        "hyp-dband-correlation",
        "hyp-bccfcc-causal-shield",
        "formal-proof-ledger",
        "formal-audit",
        "funding-landscape",
        "phoenix-observability"
      ]
    }
  ],
  "entries": [
    {
      "id": "readme",
      "source": "README.md",
      "title": "Lupine — Project README",
      "subtitle": "The error-geometry program: what is established vs. conjectured, and where to start.",
      "category": "foundations",
      "tags": [
        "overview"
      ]
    },
    {
      "id": "glossary",
      "source": "GLOSSARY.md",
      "title": "Glossary",
      "subtitle": "Terminology index for materials science, MD, DFT, and MLIPs.",
      "category": "foundations",
      "tags": [
        "glossary",
        "reference"
      ]
    },
    {
      "id": "research-index",
      "source": "docs/research-index.md",
      "title": "Research Index",
      "subtitle": "Annotated catalog of every research, planning, and presentation document.",
      "category": "foundations",
      "tags": [
        "index",
        "overview"
      ]
    },
    {
      "id": "navigation",
      "source": "docs/navigation.md",
      "title": "Repo Navigation Guide",
      "subtitle": "Quick-search codemap for finding things fast across the workspace.",
      "category": "foundations",
      "tags": [
        "navigation",
        "reference"
      ]
    },
    {
      "id": "data-provenance",
      "source": "docs/data-provenance.md",
      "title": "Data & Provenance",
      "subtitle": "Where every number comes from: OpenKIM, NIST IPR, 559 potentials, the integrity gates.",
      "category": "foundations",
      "tags": [
        "provenance",
        "data",
        "trust"
      ]
    },
    {
      "id": "internal-science-program",
      "source": "docs/internal-science-program.md",
      "title": "Internal Science Program",
      "subtitle": "The research agenda: what we are trying to learn and how the loop pursues it.",
      "category": "foundations",
      "tags": [
        "program",
        "agenda",
        "vision"
      ]
    },
    {
      "id": "public-approach",
      "source": "docs/PUBLIC.md",
      "title": "Public Corpus & Documentation Approach",
      "subtitle": "How the corpus stays public — organization model, shelves, and roadmap.",
      "category": "foundations",
      "tags": [
        "meta",
        "strategy",
        "roadmap"
      ]
    },
    {
      "id": "conjecture-ledger",
      "source": "docs/conjectures/ledger.md",
      "title": "The Hypothesis Ledger",
      "subtitle": "Every claim we have tested, its lifecycle status, and why it moved.",
      "category": "conjectures",
      "tags": [
        "ledger",
        "index",
        "overview"
      ],
      "group": "hypotheses"
    },
    {
      "id": "hyp-hyper-ribbon-universality",
      "source": "docs/conjectures/hyper-ribbon-universality.md",
      "title": "Hyper-Ribbon Universality",
      "subtitle": "Error vectors occupy a low-dimensional manifold (PR 1.05–1.86). Lean-grounded.",
      "category": "conjectures",
      "tags": [
        "hyper-ribbon",
        "sloppy-models"
      ],
      "group": "hypotheses",
      "status": "supported"
    },
    {
      "id": "hyp-hyper-ribbon-mlip-transfer",
      "source": "docs/conjectures/hyper-ribbon-mlip-transfer.md",
      "title": "Hyper-Ribbon Transfers Classical → MLIP",
      "subtitle": "Cross-paradigm ribbon transfer — per-element counts under re-audit after Born screening (2026-06); directional structure confirmed at 8–11 models.",
      "category": "conjectures",
      "tags": [
        "hyper-ribbon",
        "mlip",
        "de-myopization"
      ],
      "group": "hypotheses",
      "status": "open"
    },
    {
      "id": "hyp-cross-mlip-orthogonal-errors",
      "source": "docs/conjectures/cross-mlip-orthogonal-errors.md",
      "title": "Cross-MLIP Orthogonal Error Modes",
      "subtitle": "MACE and CHGNet fail in orthogonal directions — the precondition for ensembling.",
      "category": "conjectures",
      "tags": [
        "mlip",
        "ensemble",
        "error-geometry"
      ],
      "group": "hypotheses",
      "status": "supported"
    },
    {
      "id": "hyp-au-mlip-escape",
      "source": "docs/conjectures/au-mlip-escape.md",
      "title": "Au Escapes the Ribbon Under MLIPs",
      "subtitle": "Confirmed for MACE + CHGNet; Ag escape refuted. Mechanism open.",
      "category": "conjectures",
      "tags": [
        "au",
        "mlip",
        "escape"
      ],
      "group": "hypotheses",
      "status": "open"
    },
    {
      "id": "hyp-fe-persistent-outlier",
      "source": "docs/conjectures/fe-persistent-outlier.md",
      "title": "Fe Magnetic MLIP Failure Mode",
      "subtitle": "The old PR > 2 trio claim is frozen after Born screening; Fe remains a spin/mechanical-stability target.",
      "category": "conjectures",
      "tags": [
        "fe",
        "outlier",
        "mlip"
      ],
      "group": "hypotheses",
      "status": "open"
    },
    {
      "id": "hyp-dband-correlation",
      "source": "docs/conjectures/dband-correlation.md",
      "title": "D-Band Controls Error Correlation",
      "subtitle": "Refuted — full-sample ρ = −0.02; the signal was a sample-size confounder.",
      "category": "conjectures",
      "tags": [
        "d-band",
        "confounder",
        "matched-n"
      ],
      "group": "hypotheses",
      "status": "refuted"
    },
    {
      "id": "hyp-meam-intrinsic-2d",
      "source": "docs/conjectures/meam-intrinsic-2d.md",
      "title": "MEAM Is Intrinsically 2-D",
      "subtitle": "Refuted by matched-n bootstrap; a narrower bounded claim survives.",
      "category": "conjectures",
      "tags": [
        "meam",
        "confounder",
        "matched-n"
      ],
      "group": "hypotheses",
      "status": "refuted"
    },
    {
      "id": "hyp-bccfcc-causal-shield",
      "source": "docs/conjectures/bccfcc-causal-shield.md",
      "title": "The BCC/FCC \"Causal Shield\"",
      "subtitle": "Self-corrected — the dramatic r 0.90 vs 0.04 was 1.5% data contamination.",
      "category": "conjectures",
      "tags": [
        "bcc",
        "fcc",
        "self-correction",
        "contamination"
      ],
      "group": "hypotheses",
      "status": "self-corrected"
    },
    {
      "id": "error-geometry-objects",
      "source": "docs/science/objects.md",
      "title": "The Three Error-Geometry Objects",
      "subtitle": "Model manifold vs. participation-ratio measure vs. configuration-space core — kept straight.",
      "category": "methods",
      "tags": [
        "hyper-ribbon",
        "sloppy-models",
        "disambiguation"
      ]
    },
    {
      "id": "sloppy-models",
      "source": "docs/sloppy_models_report.md",
      "title": "Sloppy Models & Potential Transferability",
      "subtitle": "Fisher Information eigenvalue analysis — stiff vs. sloppy directions.",
      "category": "methods",
      "tags": [
        "sloppy",
        "fim"
      ]
    },
    {
      "id": "rg-coarsegraining",
      "source": "docs/rg_coarsegraining_report.md",
      "title": "Renormalization Group Coarse-Graining",
      "subtitle": "Systematically deriving effective potentials via partition-function matching.",
      "category": "methods",
      "tags": [
        "rg",
        "coarse-graining"
      ]
    },
    {
      "id": "info-theoretic",
      "source": "docs/info_theoretic_report.md",
      "title": "Information-Theoretic Bounds on Model Error",
      "subtitle": "Kolmogorov complexity, rate-distortion, and Shannon entropy for model selection.",
      "category": "methods",
      "tags": [
        "information-theory"
      ]
    },
    {
      "id": "methodology",
      "source": "docs/methodology.md",
      "title": "Methodology — How We Know, and How We Catch Ourselves",
      "subtitle": "Matched-n, contamination gating, ecological-fallacy stratification — the reusable discipline.",
      "category": "methods",
      "tags": [
        "methodology",
        "matched-n",
        "self-correction"
      ]
    },
    {
      "id": "glimmer-multifidelity-uq",
      "source": "docs/multi_fidelity_uq_glimMER_report.md",
      "title": "Multi-Fidelity UQ & the glimMER Paradigm",
      "subtitle": "Cross-potential meta-analysis and PCA-based error correction operators.",
      "category": "methods",
      "tags": [
        "uq",
        "multi-fidelity",
        "glimMER"
      ]
    },
    {
      "id": "bayesian-active-learning",
      "source": "docs/bayesian_active_learning_report.md",
      "title": "Bayesian Active Learning for Potential Selection",
      "subtitle": "Gaussian Process surrogates across 23 potentials × 12,000 materials.",
      "category": "methods",
      "tags": [
        "bayesian",
        "active-learning"
      ]
    },
    {
      "id": "weather-climate-ensembles",
      "source": "docs/weather_climate_ensembles_report.md",
      "title": "Ensemble Methods from Climate Science",
      "subtitle": "Transferring weighting strategies from weather to atomistic simulation.",
      "category": "methods",
      "tags": [
        "ensembles",
        "climate"
      ]
    },
    {
      "id": "gnn-error-prediction",
      "source": "docs/gnn_error_prediction_report.md",
      "title": "GNNs for Predicting Potential Errors",
      "subtitle": "Predicting where a potential will fail from crystal-structure topology.",
      "category": "methods",
      "tags": [
        "gnn",
        "error-prediction"
      ]
    },
    {
      "id": "tda-error-landscapes",
      "source": "docs/tda_error_landscapes_report.md",
      "title": "Topological Data Analysis of Error Landscapes",
      "subtitle": "Persistent homology for high-dimensional error surfaces.",
      "category": "methods",
      "tags": [
        "tda",
        "topology"
      ]
    },
    {
      "id": "phonon-benchmarking",
      "source": "docs/phonon_benchmarking_report.md",
      "title": "Phonon Frequency Benchmarking",
      "subtitle": "Second-derivative tests as the gold standard for potential validation.",
      "category": "validation",
      "tags": [
        "phonon",
        "benchmark"
      ]
    },
    {
      "id": "key-findings",
      "source": "docs/KEY_FINDINGS_SUMMARY.md",
      "title": "Phonon Benchmarking — Key Findings",
      "subtitle": "Executive summary of the most consequential phonon findings for Lupine.",
      "category": "validation",
      "tags": [
        "summary",
        "phonon"
      ]
    },
    {
      "id": "mlip-cloud-baseline-distill",
      "source": "docs/mlip-cloud-baseline-distill-report.md",
      "title": "MLIP Cloud Baseline and Distill: First Real 5x5 Results",
      "subtitle": "Cloud Run completed the 25-cell MLIP baseline and produced the first backend-diverse Distill energy wins.",
      "category": "validation",
      "tags": [
        "mlip",
        "cloud-run",
        "distill",
        "baseline",
        "featured"
      ],
      "group": "mlip-flywheel",
      "status": "supported"
    },
    {
      "id": "mlip-ni-paired-accuracy-live",
      "source": "docs/mlip-ni-paired-accuracy-live-report.md",
      "title": "Ni Paired Accuracy Live Report",
      "subtitle": "Live baseline-versus-Distill Accuracy evidence for the Ni fcc EAM-home-turf campaign.",
      "category": "validation",
      "tags": [
        "mlip",
        "distill",
        "ni",
        "cloud-run",
        "live-lab"
      ],
      "group": "mlip-flywheel",
      "status": "live"
    },
    {
      "id": "mlip-ni-zero-point-policy-replay",
      "source": "docs/mlip-ni-zero-point-policy-replay.md",
      "title": "Ni Zero-Point Policy Replay",
      "subtitle": "Local Rust replay turns the Ni promotion canary green before a Cloud Run image rebuild.",
      "category": "validation",
      "tags": [
        "mlip",
        "distill",
        "ni",
        "hyperribbon",
        "live-lab"
      ],
      "group": "mlip-flywheel",
      "status": "supported"
    },
    {
      "id": "mlip-mptrj-broad-dft-canary",
      "source": "docs/mlip-mptrj-broad-dft-canary.md",
      "title": "MPtrj Broad-DFT MLIP Canary",
      "subtitle": "Support-floor v2 improves MACE, ORB, and SevenNet while CHGNet safely holds: six wins, two holds, zero regressions.",
      "category": "validation",
      "tags": [
        "mlip",
        "distill",
        "mptrj",
        "dft",
        "cloud-run",
        "live-lab"
      ],
      "group": "mlip-flywheel",
      "status": "supported"
    },
    {
      "id": "projection-law-round2-preregistration",
      "source": "docs/projection-law-round2-preregistration.md",
      "title": "Round 2 Preregistration — MatPES MLIP Elastic Constants",
      "subtitle": "Pre-registered protocol: 16 cubic elements, four MatPES potentials, two functionals, and the operator-correction kill conditions.",
      "category": "validation",
      "tags": [
        "mlip",
        "matpes",
        "elasticity",
        "preregistration",
        "projection-law"
      ],
      "group": "mlip-flywheel",
      "status": "supported"
    },
    {
      "id": "projection-law-round2-results",
      "source": "docs/projection-law-round2-results.md",
      "title": "Round 2 Results — MatPES MLIP Elastic Constants across 16 Cubic Elements",
      "subtitle": "1×1×1 vs 3×3×3 supercell convergence, per-model MAE, and the Lupine correction operator on MatPES PBE and r2SCAN.",
      "category": "validation",
      "tags": [
        "mlip",
        "matpes",
        "elasticity",
        "round2",
        "projection-law",
        "live-lab"
      ],
      "featured": true,
      "featuredRole": "anchor",
      "group": "mlip-flywheel",
      "status": "live"
    },
    {
      "id": "layer2-supercell-evaluation",
      "source": "docs/layer2_supercell_evaluation.md",
      "title": "Layer 2 Supercell Scaling Evaluation",
      "subtitle": "Technical memo: elastic constants are converged at the 1×1×1 conventional cell; 3×3×3 adds runtime without accuracy gain.",
      "category": "validation",
      "tags": [
        "mlip",
        "matpes",
        "supercell",
        "convergence",
        "projection-law"
      ],
      "group": "mlip-flywheel",
      "status": "supported"
    },
    {
      "id": "layer2-research-paper",
      "source": "docs/layer2_research_paper.md",
      "title": "MatPES MLIP Elastic Constants: A 16-Element Benchmark",
      "subtitle": "Draft research paper covering methods, results, and implications for machine-learning interatomic potentials.",
      "category": "validation",
      "tags": [
        "mlip",
        "matpes",
        "elasticity",
        "paper",
        "projection-law"
      ],
      "featured": true,
      "featuredRole": "newest",
      "group": "mlip-flywheel",
      "status": "supported"
    },
    {
      "id": "formal-vision",
      "source": "docs/formal-vision.md",
      "title": "The Open Distillation Factory — Executable Vision",
      "subtitle": "Current status: 77 build-locked theorems, ~225 declarations, 2,891-job build green, and a build-locking epistemic contract.",
      "category": "formalization",
      "tags": [
        "lean",
        "formal-spec",
        "vision"
      ]
    },
    {
      "id": "formal-methodology",
      "source": "docs/formal-methodology.md",
      "title": "In the In Between",
      "subtitle": "Why we formalize before we simulate. A methodology for theorem-driven validation.",
      "category": "formalization",
      "tags": [
        "lean",
        "methodology",
        "epistemology"
      ]
    },
    {
      "id": "formal-audit",
      "source": "docs/formal-audit.md",
      "title": "Formal Audit Report",
      "subtitle": "Split verdict: Simpson's paradox fabricated, hyper-ribbon consistent but ungrounded.",
      "category": "formalization",
      "tags": [
        "lean",
        "audit",
        "verification"
      ]
    },
    {
      "id": "formal-hypotheses",
      "source": "docs/formal-hypotheses.md",
      "title": "Six Meta-Scientific Hypotheses",
      "subtitle": "From validation incompleteness to bootstrap collapse — the new research agenda.",
      "category": "formalization",
      "tags": [
        "lean",
        "hypotheses",
        "meta-science"
      ]
    },
    {
      "id": "formal-proof-ledger",
      "source": "docs/formal-proof-ledger.md",
      "title": "Formal Proof Ledger",
      "subtitle": "Which claims a Lean theorem backs — proven, fabricated, or deliberately not formalized.",
      "category": "formalization",
      "tags": [
        "lean",
        "proof-ledger",
        "audit"
      ],
      "group": "hypotheses",
      "status": "proven"
    },
    {
      "id": "changelog",
      "source": "CHANGELOG.md",
      "title": "Changelog & Progress",
      "subtitle": "What changed, why, results, and suggested next steps. Read this first.",
      "category": "changelog",
      "tags": [
        "changelog",
        "progress",
        "narrative"
      ]
    },
    {
      "id": "working-papers",
      "source": "docs/papers-working.md",
      "title": "Working Papers: The Projection Law & The Causal Geometry of Prediction Errors",
      "subtitle": "Web + print editions: abstracts, figures, key results, typeset PDFs, and the public replication kit.",
      "category": "changelog",
      "tags": [
        "papers",
        "projection-law",
        "replication",
        "featured"
      ],
      "featured": true,
      "featuredRole": "replication"
    },
    {
      "id": "research-evolution",
      "source": "docs/research_evolution_2026_05_05.md",
      "title": "The Loop That Caught Itself",
      "subtitle": "Research evolution report — how the corpus refuted its own exciting findings.",
      "category": "changelog",
      "tags": [
        "self-correction",
        "research-evolution",
        "narrative"
      ]
    },
    {
      "id": "phoenix-observability",
      "source": "docs/phoenix-observability.md",
      "title": "Phoenix: Making the Research Loop Observable",
      "subtitle": "Why we wired Phoenix, the Cloudflare edge limit we proved, and how to get more value from it.",
      "category": "changelog",
      "tags": [
        "phoenix",
        "observability",
        "evals",
        "featured"
      ]
    },
    {
      "id": "mlip-flywheel-readiness",
      "source": "docs/mlip-flywheel-readiness.md",
      "title": "MLIP Flywheel Readiness",
      "subtitle": "Cloudflare is deployed, gated, and ready for scientist review before the next expensive Distill campaign.",
      "category": "changelog",
      "tags": [
        "mlip",
        "flywheel",
        "cloudflare",
        "phoenix"
      ],
      "status": "open"
    },
    {
      "id": "born-screening-re-audit",
      "source": "docs/born-screening-re-audit.md",
      "title": "What Survived the Born-Screening Re-Audit?",
      "subtitle": "A public correction: the old MLIP 14/15 count is frozen; screened directional structure survives as the live claim.",
      "category": "changelog",
      "tags": [
        "mlip",
        "born-stability",
        "self-correction",
        "hyper-ribbon",
        "featured"
      ],
      "featured": true,
      "featuredRole": "counter",
      "status": "self-corrected"
    },
    {
      "id": "foundation-model-trust-layers",
      "source": "docs/foundation-model-trust-layers.md",
      "title": "Foundation Materials Models Need Trust Layers",
      "subtitle": "A ranked next-round target memo: batteries, MPtrj, Ni defects, Fe magnetism, Au surfaces, and phonons as evidence-carrying canaries.",
      "category": "changelog",
      "tags": [
        "mlip",
        "materials-discovery",
        "trust-layer",
        "batteries",
        "featured"
      ]
    },
    {
      "id": "references",
      "source": "docs/references.md",
      "title": "References & Intellectual Lineage",
      "subtitle": "The 35 external works we build on — each with what it is and why we cite it.",
      "category": "references",
      "tags": [
        "references",
        "bibliography",
        "lineage"
      ]
    },
    {
      "id": "lit-review-error-structure",
      "source": "lit-review.md",
      "title": "Error Structure in Interatomic Potentials — Literature Review",
      "subtitle": "Sloppy models, Simpson’s paradox, and FCC error manifolds: a 30-reference synthesis.",
      "category": "references",
      "tags": [
        "literature-review",
        "sloppy",
        "simpson",
        "fcc"
      ]
    },
    {
      "id": "academic-review-projection-law",
      "source": "docs/reviews/academic-review-projection-law-2026-06-16.md",
      "title": "Academic Review — Projection Law / IMMI Paper Suite",
      "subtitle": "Independent adversarial review: strengths, six MUST-FIX items, and recommended gates before submission.",
      "category": "references",
      "tags": [
        "review",
        "projection-law",
        "submission-gate"
      ],
      "status": "open"
    },
    {
      "id": "adversarial-review-projection-law",
      "source": "docs/reviews/adversarial-review-projection-law-2026-06-16.md",
      "title": "Adversarial Review — Projection Law / IMMI Paper Suite",
      "subtitle": "Second-pass review of the first-pass fixes: checklist, new issues, and consistency verification.",
      "category": "references",
      "tags": [
        "review",
        "projection-law",
        "submission-gate"
      ],
      "status": "open"
    },
    {
      "id": "funding-landscape",
      "source": "docs/funding_landscape_report.md",
      "title": "Federal Funding Landscape (2025–2026)",
      "subtitle": "NSF DMREF, DOE BES, DARPA SURGE/PRIME, and MGI strategic priorities.",
      "category": "references",
      "tags": [
        "funding",
        "policy"
      ]
    },
    {
      "id": "operating-system",
      "source": "docs/operating-system.md",
      "title": "Lupine Operating System",
      "subtitle": "How the research loop fits together: agenda, ledger, evidence, and correction.",
      "category": "operations",
      "tags": [
        "meta",
        "system"
      ]
    },
    {
      "id": "resource-fabric",
      "source": "docs/resource-fabric.md",
      "title": "Infrastructure Fabric",
      "subtitle": "The compute and storage fabric that reproduces every Lupine result.",
      "category": "operations",
      "tags": [
        "meta",
        "infrastructure"
      ]
    },
    {
      "id": "reproduce",
      "source": "docs/reproduce.md",
      "title": "Reproduce Our Results",
      "subtitle": "The atlas-distill + Lean commands that regenerate every ledger claim and verdict.",
      "category": "operations",
      "tags": [
        "reproducibility",
        "atlas-distill",
        "lean"
      ]
    },
    {
      "id": "extraction-complete",
      "source": "docs/EXTRACTION_COMPLETE.md",
      "title": "Extraction — Complete",
      "subtitle": "How the PDFs/DOCX were turned into this library.",
      "category": "operations",
      "tags": [
        "meta",
        "build"
      ],
      "group": "extraction"
    },
    {
      "id": "extraction-report",
      "source": "docs/EXTRACTION_REPORT.md",
      "title": "Extraction — Report",
      "subtitle": "Conversion statistics and fidelity notes.",
      "category": "operations",
      "tags": [
        "meta",
        "build"
      ],
      "group": "extraction"
    },
    {
      "id": "extraction-notes",
      "source": "docs/EXTRACTION_NOTES.md",
      "title": "Extraction — Notes",
      "subtitle": "Edge cases encountered and how they were handled.",
      "category": "operations",
      "tags": [
        "meta",
        "build"
      ],
      "group": "extraction"
    },
    {
      "id": "adr-0001-storage",
      "source": "docs/decisions/0001-r2-over-bandwidth-alliance.md",
      "title": "ADR-0001 — Hybrid GCS + R2 Storage",
      "subtitle": "Why hybrid object storage, and why we deferred Cloudflare-fronted GCS.",
      "category": "operations",
      "tags": [
        "adr",
        "infrastructure",
        "storage"
      ]
    },
    {
      "id": "partnerships",
      "source": "docs/partnerships.md",
      "title": "Partnerships",
      "subtitle": "MIIT-67 pilot mapping and the Lupine thesis — public layer.",
      "category": "operations",
      "tags": [
        "partnerships",
        "miit-67",
        "pilots"
      ]
    },
    {
      "id": "what-is-an-interatomic-potential",
      "source": "docs/what-is-an-interatomic-potential.md",
      "title": "What Is an Interatomic Potential?",
      "subtitle": "A five-minute primer on the models that let computers simulate atoms, and why they are necessary but wrong in structured ways.",
      "category": "foundations",
      "tags": [
        "primer",
        "mlip",
        "basics"
      ]
    },
    {
      "id": "projection-law-in-plain-language",
      "source": "docs/projection-law-in-plain-language.md",
      "title": "The Projection Law in Plain Language",
      "subtitle": "A 300-word explanation of what the Lupine correction operator does for a materials scientist.",
      "category": "validation",
      "tags": [
        "primer",
        "projection-law",
        "mlip"
      ],
      "group": "mlip-flywheel"
    }
  ]
};
