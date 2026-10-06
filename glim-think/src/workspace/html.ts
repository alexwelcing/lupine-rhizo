import { workspaceStyles } from "./generated/client";
export { workspaceJavaScript } from "./generated/client";

export function workspaceHtml(): string {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>Rhizo · Research workspace</title><style>${workspaceStyles}</style></head><body><div id="root"></div><noscript>This research workspace needs JavaScript. Your saved evidence remains available in the Research Library.</noscript><script type="module" src="/workspace/app.js"></script></body></html>`;
}
