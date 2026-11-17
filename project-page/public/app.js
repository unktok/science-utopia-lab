let language = 'en';
let objective = 'content-utility';
const translatable = [...document.querySelectorAll('[data-ja]')];
for (const element of translatable) element.dataset.en = element.innerHTML;
const methods = [
  {name:'Uniform priority',color:'#147d78'},
  {name:'Adaptive priority',color:'#866ca8'},
  {name:'Free code / graph',color:'#c06139'}
];
let evidence;
function chart() {
  if (!evidence) return;
  const data = evidence.paths.filter(row => row.objective === objective);
  const reference = evidence.reference_minima[objective];
  const values = data.flatMap(row => row.losses.filter(value => value !== null));
  const maximum = Math.max(...values,reference), minimum = Math.min(...values,reference);
  const top = maximum + 1.5, bottom = minimum - 1.5;
  const x = index => 70 + index * 255;
  const y = value => 25 + (top-value)/(top-bottom)*220;
  const fixed = value => Number(value.toFixed(4)).toString();
  const svg = ['<svg viewBox="0 0 910 290" role="img" aria-labelledby="chart-title chart-desc"><title id="chart-title">Submitted candidate losses across four generations</title><desc id="chart-desc">Three methods compared with a strong reference. Lower is better. The free utility method has a missing execution outcome at generation one. The exact values are available in the expandable table below.</desc>'];
  for (let step=0;step<5;step++) {
    const value = bottom + (top-bottom)*step/4, py=y(value);
    svg.push(`<line x1="60" x2="875" y1="${py}" y2="${py}" stroke="#e0e5d9"/><text x="48" y="${py+4}" text-anchor="end">${fixed(value)}</text>`);
  }
  svg.push(`<line x1="60" x2="875" y1="${y(reference)}" y2="${y(reference)}" stroke="#71826f" stroke-dasharray="5 5"/><text x="873" y="${y(reference)-8}" text-anchor="end">REF ${fixed(reference)}</text>`);
  for (let index=0;index<4;index++) svg.push(`<text x="${x(index)}" y="275" text-anchor="middle">g${index}</text>`);
  data.forEach((row, method) => {
    for (let i=1;i<row.losses.length;i++) {
      if(row.losses[i] !== null && row.losses[i-1] !== null) svg.push(`<line x1="${x(i-1)}" y1="${y(row.losses[i-1])}" x2="${x(i)}" y2="${y(row.losses[i])}" stroke="${methods[method].color}" stroke-width="2.5" opacity=".8"/>`);
    }
    row.losses.forEach((value,i) => {
      if (value === null) {svg.push(`<text x="${x(i)}" y="56" text-anchor="middle" fill="#c06139">× execution null</text>`);return;}
      svg.push(`<circle cx="${x(i)}" cy="${y(value)}" r="${6-method}" fill="${methods[method].color}" stroke="#fbfcf8" stroke-width="1.2"><title>${methods[method].name} g${i}: ${value}</title></circle>`);
    });
  });
  svg.push('</svg>');
  document.querySelector('#loss-chart').innerHTML=svg.join('');
  const nullLabel = language==='ja'?'実行 null':'Execution null';
  document.querySelector('#loss-table').innerHTML=`<table><caption>${language==='ja'?'各候補の損失（低い方が良い）':'Submitted losses (lower is better)'}</caption><thead><tr><th scope="col">Method</th><th scope="col">g0</th><th scope="col">g1</th><th scope="col">g2</th><th scope="col">g3</th></tr></thead><tbody>${data.map((row,index)=>`<tr><th scope="row">${methods[index].name}</th>${row.losses.map(value=>`<td>${value===null?nullLabel:fixed(value)}</td>`).join('')}</tr>`).join('')}<tr><th scope="row">Strong reference</th><td colspan="4">${fixed(reference)}</td></tr></tbody></table>`;
  document.querySelector('#loss-definition').textContent = `${objective==='content-utility'?'Lᵤ = −U':'L꜀ = −U + 0.1 K_collected'} · ${language==='ja'?'低い方が良い':'lower is better'}`;
}
document.querySelector('#language').addEventListener('click',()=>{
  language=language==='en'?'ja':'en';
  document.documentElement.lang=language;
  for(const element of translatable) element.innerHTML=element.dataset[language];
  document.querySelector('#language').textContent=language==='en'?'日本語':'English';
  document.querySelector('#language').setAttribute('aria-label',language==='en'?'Switch to Japanese':'Switch to English');
  chart();
});
document.querySelectorAll('[data-objective]').forEach(button=>button.addEventListener('click',()=>{
  objective=button.dataset.objective;
  document.querySelectorAll('[data-objective]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
  chart();
}));
fetch('evidence.json').then(response=>{if(!response.ok)throw Error('Evidence unavailable');return response.json();}).then(data=>{evidence=data;chart();}).catch(()=>{
  document.querySelector('#loss-chart').textContent='Evidence data could not be loaded. No values inferred. See the original closure record.';
});
