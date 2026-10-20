/* First-party API explorer. No remote scripts, inline handlers, or persistence. */
'use strict';
(() => {
  const operations = document.getElementById('operations');
  const message = document.getElementById('message');
  const filter = document.getElementById('filter');
  let schema;
  const element = (tag, text, className) => {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = text;
    if (className) result.className = className;
    return result;
  };
  const resolve = value => value && value.$ref && value.$ref.startsWith('#/components/schemas/')
    ? schema.components?.schemas?.[value.$ref.split('/').pop()] || {} : value || {};
  const sample = (value, key = '', depth = 0) => {
    const spec = resolve(value);
    if (depth > 5) return null;
    if (spec.default !== undefined) return spec.default;
    if (spec.example !== undefined) return spec.example;
    if (spec.enum) return spec.enum[0];
    if (spec.anyOf || spec.oneOf) return sample((spec.anyOf || spec.oneOf).find(item => item.type !== 'null') || {}, key, depth + 1);
    if (spec.type === 'object' || spec.properties) return Object.fromEntries(Object.entries(spec.properties || {}).map(([name, child]) => [name, sample(child, name, depth + 1)]));
    if (spec.type === 'array') return [sample(spec.items, key, depth + 1)];
    if (spec.type === 'integer' || spec.type === 'number') return spec.minimum || 1;
    if (spec.type === 'boolean') return false;
    if (key === 'email') return 'you@example.com';
    if (key === 'password') return 'replace-with-your-password';
    if (key === 'name') return 'Your name';
    return 'string';
  };
  const describe = value => {
    const spec = resolve(value);
    const types = spec.anyOf?.map(child => child.type || 'object').join(' | ') || spec.type || 'object';
    const parts = [types];
    if (spec.enum) parts.push('one of ' + spec.enum.join(', '));
    if (spec.minLength) parts.push('minimum ' + spec.minLength + ' characters');
    if (spec.maxLength) parts.push('maximum ' + spec.maxLength + ' characters');
    if (spec.minimum !== undefined) parts.push('minimum ' + spec.minimum);
    return parts.join(' · ');
  };
  const render = (path, method, spec, index) => {
    const card = element('details', undefined, 'operation');
    card.dataset.search = (method + ' ' + path + ' ' + (spec.summary || '') + ' ' + (spec.description || '')).toLowerCase();
    const summary = element('summary');
    summary.append(element('span', method.toUpperCase(), 'method ' + method), element('span', path, 'path'), element('span', spec.summary || '', 'summary-description'));
    const content = element('div', undefined, 'operation-body');
    if (spec.description) content.append(element('p', spec.description, 'description'));
    const form = element('form');
    const parameters = [];
    for (const parameter of spec.parameters || []) {
      if (!['path', 'query'].includes(parameter.in)) continue;
      const label = element('label', undefined, 'field');
      const caption = element('span', parameter.name);
      caption.append(element('small', parameter.in + (parameter.required ? ' · required' : ' · optional')));
      const input = element('input');
      input.id = 'parameter-' + index + '-' + parameter.name;
      input.name = parameter.name;
      input.type = 'text';
      input.required = Boolean(parameter.required);
      input.placeholder = parameter.name === 'run_id' ? 'Run UUID returned by POST /api/runs' : parameter.name === 'name' ? 'release.zip' : describe(parameter.schema);
      label.append(caption, input);
      form.append(label);
      parameters.push({ parameter, input });
    }
    let body;
    const bodySpec = spec.requestBody?.content?.['application/json']?.schema;
    if (bodySpec) {
      form.append(element('h2', 'JSON request body'));
      const resolved = resolve(bodySpec);
      const fields = element('ul', undefined, 'schema-list');
      for (const [name, property] of Object.entries(resolved.properties || {})) {
        const row = element('li');
        row.append(element('strong', name), document.createTextNode(' · ' + (resolved.required?.includes(name) ? 'required · ' : '') + describe(property)));
        fields.append(row);
      }
      form.append(fields);
      const label = element('label', undefined, 'field');
      label.append(element('span', 'Editable request JSON'));
      body = element('textarea');
      body.spellcheck = false;
      body.value = JSON.stringify(sample(bodySpec), null, 2);
      label.append(body);
      form.append(label);
    }
    const responseTypes = Object.entries(spec.responses || {}).map(([code, response]) => code + ' ' + (response.description || '')).join(' · ');
    content.append(element('h2', 'Documented responses'), element('p', responseTypes, 'description'));
    const sendRow = element('div', undefined, 'send-row');
    const send = element('button', 'Send request');
    send.type = 'submit';
    const state = element('span', '', 'request-state');
    state.setAttribute('role', 'status');
    sendRow.append(send, state);
    form.append(sendRow);
    const output = element('div', undefined, 'response');
    content.append(form, output);
    let downloadUrl;
    form.addEventListener('submit', async event => {
      event.preventDefault();
      let url = path;
      const query = new URLSearchParams();
      for (const { parameter, input } of parameters) {
        if (parameter.in === 'path') url = url.replace('{' + parameter.name + '}', encodeURIComponent(input.value));
        else if (input.value) query.set(parameter.name, input.value);
      }
      if (query.size) url += '?' + query.toString();
      const headers = { Accept: 'application/json' };
      const request = { method: method.toUpperCase(), headers, credentials: 'same-origin' };
      try {
        if (body) request.body = JSON.stringify(JSON.parse(body.value));
        else if (['post', 'put', 'patch', 'delete'].includes(method)) request.body = '{}';
      } catch {
        state.textContent = 'Enter valid JSON before sending.';
        return;
      }
      if (request.body !== undefined) headers['Content-Type'] = 'application/json';
      if (downloadUrl) URL.revokeObjectURL(downloadUrl);
      output.replaceChildren();
      send.disabled = true;
      state.textContent = 'Sending to ' + location.origin + '…';
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000);
      request.signal = controller.signal;
      try {
        const started = performance.now();
        const response = await fetch(url, request);
        state.textContent = Math.round(performance.now() - started) + ' ms';
        output.append(element('p', 'HTTP ' + response.status + ' ' + response.statusText, 'http-status' + (response.ok ? '' : ' error')));
        if (response.headers.get('content-type')?.includes('application/zip')) {
          const blob = await response.blob();
          downloadUrl = URL.createObjectURL(blob);
          const link = element('a', 'Download response artifact (' + blob.size + ' bytes)', 'download');
          link.href = downloadUrl;
          link.download = 'aftercare-artifact.zip';
          output.append(link);
        } else {
          let text = await response.text();
          try { text = JSON.stringify(JSON.parse(text), null, 2); } catch { /* Preserve non-JSON response text. */ }
          output.append(element('pre', text.length > 100000 ? text.slice(0, 100000) + '\n[Display truncated at 100,000 characters]' : text));
        }
      } catch (error) {
        state.textContent = error.name === 'AbortError' ? 'Request timed out after 30 seconds.' : 'Request failed. Check your connection and retry.';
      } finally {
        clearTimeout(timeout);
        send.disabled = false;
      }
    });
    card.append(summary, content);
    operations.append(card);
  };
  filter.addEventListener('input', () => {
    for (const card of operations.children) card.hidden = !card.dataset.search.includes(filter.value.trim().toLowerCase());
  });
  fetch('/api/openapi.json', { credentials: 'same-origin', headers: { Accept: 'application/json' } })
    .then(response => { if (!response.ok) throw new Error('Schema unavailable'); return response.json(); })
    .then(value => {
      schema = value;
      document.getElementById('version').textContent = schema.info.title + ' · v' + schema.info.version;
      let count = 0;
      for (const [path, methods] of Object.entries(schema.paths || {})) {
        if (!(path.startsWith('/api/') || path === '/healthz')) continue;
        for (const [method, spec] of Object.entries(methods)) {
          if (['get', 'post', 'put', 'patch', 'delete'].includes(method)) render(path, method, spec, count++);
        }
      }
      message.textContent = count + ' operations from the live schema. Open an endpoint to inspect its fields or send a request.';
    })
    .catch(() => { message.textContent = 'Could not load the schema. Reload this page or open the OpenAPI JSON link above.'; });
})();
