import { h } from "./dom.js";
import { codeBlock } from "./components/tg-code-block.js";

const HEADING = /^[A-Z][^\n]*:$/;

function dedent(lines) {
  const indents = lines.filter((line) => line.trim()).map((line) => line.length - line.trimStart().length);
  const cut = indents.length ? Math.min(...indents) : 0;
  return lines.map((line) => line.slice(cut));
}

function bullets(lines) {
  const items = [];
  for (const line of lines) {
    if (/^\s*- /.test(line)) items.push(line.replace(/^\s*- /, "").trim());
    else if (line.trim() && items.length) items[items.length - 1] += ` ${line.trim()}`;
  }
  return items;
}

const ROW = /^(\S+)\s{2,}(\S.*)$/;
const OPTION = /^([a-z_]{2,24}): (\S.*)$/;

function joined(lines) {
  return lines.map((line) => line.trim()).join(" ");
}

function groups(lines, pattern) {
  const rows = [];
  const base = Math.min(...lines.map((line) => line.length - line.trimStart().length));
  for (const line of lines) {
    const match = pattern.exec(line.slice(base));
    if (match && line.length - line.trimStart().length === base) rows.push([match[1], match[2]]);
    else if (rows.length && line.trim()) rows[rows.length - 1][1] += ` ${line.trim()}`;
    else return null;
  }
  return rows;
}

function block(lines) {
  const indented = lines.every((line) => /^\s{2,}/.test(line));
  const rows = indented ? groups(lines, ROW) : null;
  if (rows && rows.length > 1) {
    return h("table", {}, h("tbody", {}, rows.map(([name, text]) => h("tr", {}, h("td", {}, h("code", {}, name)), h("td", {}, text)))));
  }
  const options = groups(lines, OPTION);
  if (options && options.length > 1) {
    return h("ul", {}, options.map(([name, text]) => h("li", {}, h("code", {}, name), `: ${text}`)));
  }
  return h("p", {}, joined(lines));
}

function blocks(lines) {
  const nodes = [];
  let current = [];
  const flush = () => {
    if (current.length) nodes.push(block(current));
    current = [];
  };
  for (const line of lines) {
    if (line.trim()) current.push(line);
    else flush();
  }
  flush();
  return nodes;
}

function section(title, lines) {
  const body = dedent(lines);
  if (/^how to use/i.test(title)) {
    const end = lines.findIndex((line, index) => index > 0 && line.trim() && !/^\s/.test(line));
    const code = dedent(end === -1 ? lines : lines.slice(0, end));
    const rest = end === -1 ? [] : lines.slice(end);
    return [h("h2", {}, "How to use it"), codeBlock(code.join("\n").replace(/^\n+|\s+$/g, "")), ...blocks(rest)];
  }
  const nodes = [h("h2", {}, title.replace(/:$/, ""))];
  const items = bullets(body);
  if (items.length) nodes.push(h("ul", {}, items.map((text) => h("li", {}, text))));
  else nodes.push(...blocks(body));
  return nodes;
}

export function renderDescription(text) {
  const lines = text.split("\n");
  const nodes = [];
  let title = null;
  let body = [];
  const flush = () => {
    if (title) nodes.push(...section(title, body));
  };
  let intro = [];
  for (const line of lines.slice(1)) {
    if (HEADING.test(line)) {
      if (!title) nodes.push(...blocks(intro));
      flush();
      title = line;
      body = [];
    } else if (title) body.push(line);
    else intro.push(line);
  }
  if (!title) nodes.push(...blocks(intro));
  flush();
  return nodes;
}
