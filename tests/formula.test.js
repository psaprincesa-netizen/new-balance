import test from "node:test";
import assert from "node:assert/strict";
import { cellValue, parseCSV, toCSV } from "../web/formula.js";
test("references, precedence, ranges and localized functions", () => {
  const g = [
    ["10", "20", "=A1+B1*2"],
    ["5", "=SOMA(A1:A2)", "=MÉDIA(A1:B1)"],
    ["=ARRED(10/3;2)", "=SE(0;10;20)", "=ABS(-4)"],
  ];
  assert.equal(cellValue(g, 0, 2), 50);
  assert.equal(cellValue(g, 1, 1), 15);
  assert.equal(cellValue(g, 1, 2), 15);
  assert.equal(cellValue(g, 2, 0), 3.33);
  assert.equal(cellValue(g, 2, 1), 20);
  assert.equal(cellValue(g, 2, 2), 4);
});
test("cycles, bad references, division and code are rejected", () => {
  assert.equal(cellValue([["=B1", "=A1"]], 0, 0), "#CICLO!");
  assert.equal(cellValue([["=1/0"]], 0, 0), "#DIV/0!");
  for (const expression of [
    "=Z99",
    "=process.exit()",
    "=1+2 garbage",
    "=SOMA()",
    "=1;2",
  ])
    assert.equal(cellValue([[expression]], 0, 0), "#ERRO!");
});
test("CSV quotes, separators, line breaks and empty rows roundtrip", () => {
  const rows = [
    ["Nome", "Descrição"],
    ["Ana", 'a,b;"c"\nlinha'],
  ];
  const parsed = parseCSV(toCSV(rows));
  assert.deepEqual(
    parsed.map((r) => r.slice(0, 2)),
    rows,
  );
  assert.deepEqual(
    parseCSV("a;b\r\n1;2\r\n").map((r) => r.slice(0, 2)),
    [
      ["a", "b"],
      ["1", "2"],
    ],
  );
  assert.throws(() => parseCSV('"sem fim'));
  assert.throws(() => parseCSV(Array(202).fill("a").join("\n")));
});
test('workbook references, lookups, text, conditions and financial formulas', () => {
  const cost={name:'Custos',cells:[['Item','Valor'],['A','10'],['B','20']]};
  const summary={name:'Resumo',cells:[['=SOMA(Custos!B2:B3)','=PROCV("B";Custos!A2:B3;2;FALSE)'],['=SE(1>0;"Sim";"Não")','=CONCAT("Nome: ";ESQUERDA("Drap";2))'],['=PGTO(0;10;1000)','=CONT.SE(Custos!B2:B3;">15")'],['=MED(1;9;3)','=MAX(1;5;2)']]};
  const book=[cost,summary];
  const get=(r,c)=>cellValue(summary.cells,r,c,new Set(),book);
  assert.equal(get(0,0),30);assert.equal(get(0,1),20);
  assert.equal(get(1,0),'Sim');assert.equal(get(1,1),'Nome: Dr');
  assert.equal(get(2,0),-100);assert.equal(get(2,1),1);
  assert.equal(get(3,0),3);assert.equal(get(3,1),5);
  cost.cells[1][1]='15';assert.equal(get(0,0),35);
  cost.cells[1][1]='=Resumo!A1';assert.equal(get(0,0),'#CICLO!');
  assert.equal(cellValue([['=WEBSERVICE("https://example.invalid")']],0,0),'#ERRO!');
});
