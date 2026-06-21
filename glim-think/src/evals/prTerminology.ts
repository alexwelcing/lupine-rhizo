export interface ParticipationRatioTerminologyEval {
  relevant: boolean;
  score: number;
  label: "pass" | "fail" | "skip";
  explanation: string;
}

const PR_TERMS = [
  /\bparticipation ratio\b/i,
  /\bPR\b/,
  /\beffective dimension\b/i,
  /\bhyper-?ribbon\b/i,
];

const MLIP_MANIFOLD_CONTEXT = [
  /\bMLIP\b/i,
  /\bLAM\b/i,
  /\bmanifold\b/i,
  /\belastic(?:-|\s)?constant/i,
  /\bC11\b/i,
  /\bC12\b/i,
  /\bC44\b/i,
  /\berror covariance\b/i,
  /\brelative[-\s]?error\b/i,
];

const WRONG_SENSE = [
  /\bphonon\b/i,
  /\bq[-\s]?point\b/i,
  /\bsupercell\b/i,
  /\bacoustic mode\b/i,
  /\blow[-\s]?frequency\b/i,
  /\bmode localization\b/i,
  /\bdelocalized(?:\/| or )?affine\b/i,
  /\bvibrational mode\b/i,
];

function hasAny(patterns: RegExp[], text: string): boolean {
  return patterns.some((pattern) => pattern.test(text));
}

function hasFullRequiredSense(text: string): boolean {
  const hasCovariance = /\bcovariance\b/i.test(text);
  const hasSpectrum = /\beigenvalue|eigenspectrum|spectrum\b|sum.*lambda/i.test(text);
  const hasErrorGeometry = /\beffective dimension\b|error vector|relative[-\s]?error/i.test(text);
  return hasCovariance && hasSpectrum && hasErrorGeometry;
}

export function evaluateParticipationRatioTerminology(
  prompt: string,
  text: string,
): ParticipationRatioTerminologyEval {
  const combined = `${prompt}\n${text}`;
  const relevant = hasAny(PR_TERMS, combined) && hasAny(MLIP_MANIFOLD_CONTEXT, combined);
  if (!relevant) {
    return {
      relevant: false,
      score: 1,
      label: "skip",
      explanation: "No MLIP/manifold participation-ratio terminology to evaluate.",
    };
  }

  const hasRequiredSense = hasFullRequiredSense(text);
  const hasWrongSense = hasAny(WRONG_SENSE, text);
  if (hasRequiredSense && !hasWrongSense) {
    return {
      relevant: true,
      score: 1,
      label: "pass",
      explanation:
        "Uses the IMMI/MLIP sense of participation ratio: covariance-spectrum effective dimension of relative-error vectors.",
    };
  }
  if (hasWrongSense) {
    return {
      relevant: true,
      score: 0,
      label: "fail",
      explanation:
        "Likely used the phonon/vibrational-mode participation-ratio sense instead of the IMMI/MLIP covariance-spectrum effective-dimension sense.",
    };
  }
  return {
    relevant: true,
    score: 0.35,
    label: "fail",
    explanation:
      "Mentions MLIP/manifold participation ratio without defining it as covariance-spectrum effective dimension over relative-error vectors.",
  };
}
