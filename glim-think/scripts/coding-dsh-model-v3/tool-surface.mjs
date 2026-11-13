// Keep registrations required by the pinned Runtime's inherited allow-list,
// but do not present or execute the five placeholders that always throw.
export const UNAVAILABLE_TOOLS = Object.freeze(['skill', 'read_image', 'job_output', 'job_list', 'job_kill']);

export function restrictUnavailableTools(agent) {
  return agent.ctx.tools.restrict({ deny: [...UNAVAILABLE_TOOLS] });
}
