# Configurator interface contract

The browser workspace is developed test-first around the following public contract:

- five keyboard-operable discovery stages cover every requirement in the product brief;
- saved fictional scenarios come from the scenario API, never from client-side fixtures;
- recommendation traces preserve the requirement, rule, component, reason, alternative,
  risk, and validation produced by the deterministic engine;
- the generated architecture is displayed from the scenario SVG endpoint rather than
  inserted as untrusted markup;
- JSON, Markdown, and SVG exports are explicit user actions;
- all dynamic copy is assigned with `textContent`, and superseded network requests are
  cancelled with `AbortController`;
- mobile reflow, visible keyboard focus, status announcements, and reduced motion are
  first-class behaviours.

The first test run intentionally failed because the template, client, styles, and assets did
not exist. The production interface was then implemented against this contract.
