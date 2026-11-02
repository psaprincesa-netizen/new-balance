export function parseCSV(text, {maxRows=200,maxCols=26,minCols=6}={}) {
  const rows = [[]];
  let value = "",
    quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      if (quoted && text[i + 1] === '"') {
        value += '"';
        i++;
      } else if (quoted || !value) quoted = !quoted;
      else value += ch;
    } else if (!quoted && (ch === "," || ch === ";")) {
      rows.at(-1).push(value);
      value = "";
    } else if (!quoted && (ch === "\n" || ch === "\r")) {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      rows.at(-1).push(value);
      rows.push([]);
      value = "";
    } else value += ch;
  }
  if (quoted) throw Error("CSV com aspas não fechadas.");
  rows.at(-1).push(value);
  if (rows.length > 1 && rows.at(-1).length === 1 && rows.at(-1)[0] === "")
    rows.pop();
  if (rows.length > maxRows || Math.max(...rows.map((r) => r.length)) > maxCols)
    throw Error(`Limite: ${maxRows} linhas e ${maxCols} colunas.`);
  const width = Math.max(minCols, ...rows.map((r) => r.length));
  return rows.map((r) => Array.from({ length: width }, (_, i) => r[i] || ""));
}
export function toCSV(rows) {
  return rows
    .map((r) =>
      r.map((v) => '"' + String(v ?? "").replaceAll('"', '""') + '"').join(","),
    )
    .join("\r\n");
}
