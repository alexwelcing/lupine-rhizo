"""Y-matrix cross-property error-geometry analysis (prereg 2026-07-01).

Confirmatory machinery for the registered hypotheses in
docs/plans/y-matrix-cross-property-preregistration-2026-07-01.md:

- H1: participation ratio of the material-by-property error covariance vs a
  coupling-aware (family-wise permutation) null.
- H2: pairwise leading-mode cosine similarity across models vs the same null.
- H3: defect-family vs bulk-family median |relative error| ratio per model
  (pass >= 2.0, kill < 1.5) with a seeded bootstrap CI.

Plus a reference-free descriptive mode (cross-model disagreement /
ensemble spread) for sweeps whose reference targets are not yet bound.
"""

from lupine_distill.analysis.binding import (
    family_reference_scales,
    select_references,
)
from lupine_distill.analysis.descriptive import (
    assemble_descriptive_matrices,
    stack_matrices,
)
from lupine_distill.analysis.dimensionality import (
    covariance_eigenvalues,
    leading_mode,
    pairwise_cosine,
    participation_ratio,
)
from lupine_distill.analysis.errors import (
    AnalysisError,
    ComputationError,
    InputValidationError,
)
from lupine_distill.analysis.families import (
    CANONICAL_PROPERTIES,
    DEFAULT_BULK_PROPERTIES,
    DEFAULT_DEFECT_PROPERTIES,
    DEFAULT_FAMILY_MAP,
    DEFAULT_METHOD_PREFERENCE,
    DEFAULT_TARGET_PROPERTY_MAP,
)
from lupine_distill.analysis.loading import (
    ReferenceEntry,
    RunRecord,
    TargetLoadResult,
    load_run_directory,
    load_run_records,
    load_targets_directory,
    parse_run_payload,
    parse_targets_payload,
)
from lupine_distill.analysis.nulls import (
    NullDistribution,
    leading_mode_cosine_null,
    permute_within_families,
    pr_null_distribution,
)
from lupine_distill.analysis.report import (
    build_confirmatory_report,
    build_descriptive_report,
)
from lupine_distill.analysis.vectors import (
    ErrorCell,
    ErrorMatrix,
    NormalizedErrorValue,
    assemble_error_cells,
    assemble_error_matrix,
    normalized_signed_error,
)
from lupine_distill.analysis.weakspots import (
    CellExclusion,
    WeakSpotResult,
    weak_spot_statistic,
)

__all__ = [
    "AnalysisError",
    "CANONICAL_PROPERTIES",
    "CellExclusion",
    "ComputationError",
    "DEFAULT_BULK_PROPERTIES",
    "DEFAULT_DEFECT_PROPERTIES",
    "DEFAULT_FAMILY_MAP",
    "DEFAULT_METHOD_PREFERENCE",
    "DEFAULT_TARGET_PROPERTY_MAP",
    "ErrorCell",
    "ErrorMatrix",
    "InputValidationError",
    "NormalizedErrorValue",
    "NullDistribution",
    "ReferenceEntry",
    "RunRecord",
    "TargetLoadResult",
    "WeakSpotResult",
    "assemble_descriptive_matrices",
    "assemble_error_cells",
    "assemble_error_matrix",
    "build_confirmatory_report",
    "build_descriptive_report",
    "covariance_eigenvalues",
    "family_reference_scales",
    "leading_mode",
    "leading_mode_cosine_null",
    "load_run_directory",
    "load_run_records",
    "load_targets_directory",
    "normalized_signed_error",
    "pairwise_cosine",
    "parse_run_payload",
    "parse_targets_payload",
    "participation_ratio",
    "permute_within_families",
    "pr_null_distribution",
    "select_references",
    "stack_matrices",
    "weak_spot_statistic",
]
